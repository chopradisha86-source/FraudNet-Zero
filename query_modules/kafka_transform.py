import mgp
import json
import hashlib

def hash_pii(identifier: str) -> str:
    """
    Generates a deterministic 16-character SHA-256 hash for accounts.
    Ensures privacy compliance while maintaining consistent graph linking.
    """
    if not identifier:
        return ""
    return hashlib.sha256(str(identifier).encode('utf-8')).hexdigest()[:16]

@mgp.transformation
def transform(messages: mgp.Messages) -> mgp.Record(query=str, parameters=mgp.Nullable[mgp.Map]):
    result_queries = []
    
    for i in range(messages.total_messages()):
        message = messages.message_at(i)
        
        try:
            # Decode raw Kafka payload
            raw_bytes = message.payload()
            raw_text = raw_bytes.decode('utf-8')
            
            print(f"DEBUG: Received raw message -> {raw_text}", flush=True)
            
            payload = json.loads(raw_text)
            print(f"DEBUG: Parsed PaySim keys -> {list(payload.keys())}", flush=True)

            # Extract PaySim sender/receiver identifiers (supports nameOrig/nameDest + fallbacks)
            raw_sender = payload.get("nameOrig") or payload.get("sender") or payload.get("sender_id")
            raw_receiver = payload.get("nameDest") or payload.get("receiver") or payload.get("receiver_id")
            
            if not raw_sender or not raw_receiver:
                print(f"DEBUG: FAILED KEY MATCH! Sender: {raw_sender}, Receiver: {raw_receiver}", flush=True)
                continue

            # Pseudonymize account IDs via SHA-256
            hashed_sender = hash_pii(raw_sender)
            hashed_receiver = hash_pii(raw_receiver)

            # Cypher statement updating balances and creating directed transaction edges
            cypher = """
            MERGE (s:Account {id: $sender})
            ON CREATE SET s.balance = $source_balance, s.raw_id = $raw_sender
            ON MATCH SET s.balance = $source_balance

            MERGE (r:Account {id: $receiver})
            ON CREATE SET r.balance = $target_balance, r.raw_id = $raw_receiver
            ON MATCH SET r.balance = $target_balance

            CREATE (s)-[:TRANSFERRED {
                amount: $amount, 
                step: $step,
                tx_type: $type,
                is_fraud_ground_truth: $is_fraud,
                source_balance: $source_balance,
                target_balance: $target_balance
            }]->(r)
            """
            
            params = {
                "sender": hashed_sender,
                "receiver": hashed_receiver,
                "raw_sender": str(raw_sender),
                "raw_receiver": str(raw_receiver),
                "amount": float(payload.get("amount", 0.0)),
                "step": int(payload.get("step", 0)),
                "type": str(payload.get("type", "TRANSFER")),
                "is_fraud": int(payload.get("isFraud", 0)),
                # Node balance parameters used for Cost-Weighted Min-Cut capacity calculation
                "source_balance": float(payload.get("oldbalanceOrg", 0.0)),
                "target_balance": float(payload.get("oldbalanceDest", 0.0))
            }
            
            print(f"DEBUG: Built Cypher query for PaySim event {hashed_sender} -> {hashed_receiver}", flush=True)
            result_queries.append(mgp.Record(query=cypher, parameters=params))
            
        except Exception as e:
            print(f"DEBUG: Transformation Exception -> {str(e)}", flush=True)
            continue
            
    return result_queries