import json
import time
from confluent_kafka import Consumer, KafkaError
from gqlalchemy import Memgraph

# --- MODULAR IMPORTS ---
from gcn_core.topology_agent import extract_account_graph_features
from agents.llm_agent import analyze_transaction_with_agent

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)

# Kafka Consumer Configuration
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'memgraph-ingestion-group',
    'auto.offset.reset': 'latest'
}

consumer = Consumer(conf)
consumer.subscribe(['financial_transactions'])

def process_transaction(tx):
    """
    Ingests a single transaction into Memgraph, extracts dynamic graph features,
    and passes enriched features down the scoring pipeline.
    """
    query = """
    MERGE (s:Account {id: $sender_id})
    MERGE (r:Account {id: $receiver_id})
    CREATE (s)-[t:TRANSFERRED {
        tx_id: $tx_id,
        amount: $amount,
        timestamp: $timestamp,
        ip: $ip_address,
        device: $device_id,
        is_synthetic: $is_synthetic
    }]->(r);
    """
    
    params = {
        "sender_id": tx["sender_id"],
        "receiver_id": tx["receiver_id"],
        "tx_id": tx["transaction_id"],
        "amount": float(tx["amount"]),
        "timestamp": tx["timestamp"],
        "ip_address": tx["ip_address"],
        "device_id": tx["device_id"],
        "is_synthetic": tx.get("is_synthetic_ring", False)
    }
    
    try:
        # 1. Ingest transaction edge into Memgraph
        memgraph.execute(query, params)

        # 2. Extract real-time graph features for the sender account
        sender_features = extract_account_graph_features(tx["sender_id"])

        # 3. Build enriched feature vector for downstream scoring
        enriched_event = {
            **tx,
            "sender_graph_features": sender_features
        }

        # 4. Invoke LLM / GCN scoring agent for live evaluation
        analyze_transaction_with_agent(enriched_event)

    except Exception as e:
        print(f"❌ Error writing transaction to Memgraph: {e}")

def start_ingestion():
    print("📥 Memgraph Ingestion Consumer Started...")
    print("Listening for incoming transactions on topic 'financial_transactions'...\n")
    
    count = 0
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"❌ Kafka Consumer Error: {msg.error()}")
                    break

            # Parse Kafka message payload
            tx_data = json.loads(msg.value().decode('utf-8'))
            process_transaction(tx_data)
            
            # Micro-throttle (20 tx/sec) to ensure terminal log readability
            time.sleep(0.05)
            
            count += 1
            if count % 10 == 0:
                print(f"⚡ Ingested {count} transactions into Memgraph graph database...", end="\r")

    except KeyboardInterrupt:
        print("\nStopping ingestion consumer...")
    finally:
        consumer.close()

if __name__ == "__main__":
    start_ingestion()