import json
from confluent_kafka import Consumer, KafkaError
from gqlalchemy import Memgraph

# --- UPDATED MODULAR IMPORTS ---
from gcn_core.topology_agent import detect_micro_layering_cycles, run_louvain_community_analysis
from agents.risk_agent import analyze_and_score_accounts

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
    Ingests a single transaction into Memgraph:
    - Creates or merges Sender Account
    - Creates or merges Receiver Account
    - Connects them via a TRANSFERRED relationship
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
        memgraph.execute(query, params)
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
            
            count += 1
            if count % 10 == 0:
                print(f"⚡ Ingested {count} transactions into Memgraph graph database...", end="\r")

    except KeyboardInterrupt:
        print("\nStopping ingestion consumer...")
    finally:
        consumer.close()

if __name__ == "__main__":
    start_ingestion()