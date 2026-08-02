import mgp
import json

@mgp.transformation
def transform(messages: mgp.Messages) -> mgp.Record(query=str, parameters=mgp.Nullable[mgp.Map]):
    result_queries = []
    
    for i in range(messages.total_messages()):
        message = messages.message_at(i)
        
        try:
            # Decode raw payload
            raw_bytes = message.payload()
            raw_text = raw_bytes.decode('utf-8')
            
            # PRINT TO DOCKER LOGS FOR DEBUGGING
            print(f"DEBUG: Received raw message -> {raw_text}", flush=True)
            
            payload = json.loads(raw_text)
            
            # Print parsed JSON keys
            print(f"DEBUG: Parsed keys -> {list(payload.keys())}", flush=True)

            sender = payload.get("sender") or payload.get("sender_id") or payload.get("sender_account")
            receiver = payload.get("receiver") or payload.get("receiver_id") or payload.get("receiver_account")
            
            if not sender or not receiver:
                print(f"DEBUG: FAILED KEY MATCH! Sender: {sender}, Receiver: {receiver}", flush=True)
                continue

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
                "sender": str(sender),
                "receiver": str(receiver),
                "tx_id": str(payload.get("transaction_id", "tx_0")),
                "amount": float(payload.get("amount", 0.0)),
                "timestamp": str(payload.get("timestamp", ""))
            }
            
            print(f"DEBUG: Successfully built Cypher query for {sender} -> {receiver}", flush=True)
            result_queries.append(mgp.Record(query=cypher, parameters=params))
            
        except Exception as e:
            print(f"DEBUG: Transformation Exception -> {str(e)}", flush=True)
            continue
            
    return result_queries