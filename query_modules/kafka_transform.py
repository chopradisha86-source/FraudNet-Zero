import mgp
import json
import hashlib

def hash_pii(identifier: str) -> str:
    """
    Generates a deterministic 16-character SHA-256 hash for accounts/entities.
    Ensures privacy compliance while allowing consistent graph node linking.
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
            print(f"DEBUG: Parsed keys -> {list(payload.keys())}", flush=True)

            # Extract raw sender/receiver identifiers
            raw_sender = payload.get("sender") or payload.get("sender_id") or payload.get("sender_account")
            raw_receiver = payload.get("receiver") or payload.get("receiver_id") or payload.get("receiver_account")
            
            if not raw_sender or not raw_receiver:
                print(f"DEBUG: FAILED KEY MATCH! Sender: {raw_sender}, Receiver: {raw_receiver}", flush=True)
                continue

            # Apply SHA-256 hashing to pseudonymize account IDs before Cypher ingestion
            hashed_sender = hash_pii(raw_sender)
            hashed_receiver = hash_pii(raw_receiver)

            cypher = """
            MERGE (s:Account {id: $sender})
            MERGE (r:Account {id: $receiver})
            CREATE (s)-[:TRANSFERRED {
                transaction_id: $tx_id, 
                amount: $amount, 
                timestamp: $timestamp
            }]->(r)
            """
            
            params = {
                "sender": hashed_sender,
                "receiver": hashed_receiver,
                "tx_id": str(payload.get("transaction_id", "tx_0")),
                "amount": float(payload.get("amount", 0.0)),
                "timestamp": str(payload.get("timestamp", ""))
            }
            
            print(f"DEBUG: Built Cypher query for {hashed_sender} -> {hashed_receiver}", flush=True)
            result_queries.append(mgp.Record(query=cypher, parameters=params))
            
        except Exception as e:
            print(f"DEBUG: Transformation Exception -> {str(e)}", flush=True)
            continue
            
    return result_queries