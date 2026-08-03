import csv
import json
import os
import random
import time
from datetime import datetime
from confluent_kafka import Producer

# Kafka Configuration
KAFKA_TOPIC = "financial_transactions"
KAFKA_CONF = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(KAFKA_CONF)

# Path to your PaySim dataset file
DATASET_PATH = "transactions.csv"

def delivery_report(err, msg):
    """Callback for Kafka message delivery confirmation."""
    if err is not None:
        print(f"❌ Message delivery failed: {err}")

def produce_laundering_ring(ring_size=5, base_amount=9500.0):
    """
    Generates a synthetic cyclic money laundering ring pattern.
    Topology: A -> B -> C -> D -> A
    Uses shared device/IP metadata anomalies to simulate a coordinated mule network.
    """
    ring_nodes = [f"MULE_{random.randint(5000, 9999)}" for _ in range(ring_size)]
    ring_payloads = []
    
    # Common metadata anomalies for the ring nodes
    suspicious_ip = f"10.0.99.{random.randint(1, 50)}"
    shared_device = f"DEV_MULE_{random.randint(10, 99)}"

    for i in range(ring_size):
        sender = ring_nodes[i]
        receiver = ring_nodes[(i + 1) % ring_size]  # Complete the cycle back to first node
        
        # Slight variation in amount to simulate micro-layering deductions
        amount = round(base_amount * random.uniform(0.95, 0.99), 2)
        
        payload = {
            "transaction_id": f"TX_RING_{int(time.time() * 1000)}_{i}",
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": suspicious_ip,
            "device_id": shared_device,
            "is_synthetic_ring": True
        }
        ring_payloads.append(payload)
        
    return ring_payloads

def stream_transactions():
    print("🚀 Starting FraudNet-Zero Producer Pipeline...")
    
    # Check if PaySim dataset exists in project root
    if not os.path.exists(DATASET_PATH):
        print(f"⚠️ Warning: '{DATASET_PATH}' not found in project directory.")
        print("Please place 'transactions.csv' in the project root to stream PaySim baseline data.")
        return

    print(f"📄 Replaying PaySim dataset from '{DATASET_PATH}'...")
    print("Press Ctrl+C to stop streaming.\n")

    try:
        with open(DATASET_PATH, mode='r') as csv_file:
            reader = csv.DictReader(csv_file)
            count = 0
            
            for row in reader:
                # 1. Map PaySim dataset row to standard transaction payload
                payload = {
                    "transaction_id": f"TX_{row.get('step', '0')}_{random.randint(10000, 99999)}",
                    "sender_id": row.get("nameOrig", f"ACC_{random.randint(1000, 9999)}"),
                    "receiver_id": row.get("nameDest", f"ACC_{random.randint(1000, 9999)}"),
                    "amount": float(row.get("amount", 0.0)),
                    "timestamp": datetime.utcnow().isoformat(),
                    "ip_address": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                    "device_id": f"DEV_{random.randint(100, 999)}",
                    "is_synthetic_ring": False
                }

                # 2. Produce PaySim baseline transaction to Kafka
                producer.produce(
                    KAFKA_TOPIC,
                    key=payload["sender_id"],
                    value=json.dumps(payload),
                    callback=delivery_report
                )
                producer.poll(0)
                count += 1

                if count % 20 == 0:
                    print(f"⚡ Produced {count} PaySim transactions to Kafka...", end="\r")

                # 3. 5% chance to automatically inject a Fraudulent Laundering Ring
                if random.random() < 0.05:
                    print("\n🚨 Injecting Synthetic Laundering Ring Pattern into Stream...")
                    ring_txs = produce_laundering_ring(ring_size=random.randint(4, 6))
                    for ring_tx in ring_txs:
                        producer.produce(
                            KAFKA_TOPIC,
                            key=ring_tx["sender_id"],
                            value=json.dumps(ring_tx),
                            callback=delivery_report
                        )
                        # Rapid succession execution between mule nodes
                        time.sleep(0.03)
                    producer.flush()
                    print("🚨 Laundering Ring Injection Complete.\n")

                # Simulate real-time stream throughput speed
                time.sleep(random.uniform(0.05, 0.2))

    except KeyboardInterrupt:
        print("\nStopping transaction producer...")
    finally:
        producer.flush()
        print("Producer shut down successfully.")

if __name__ == "__main__":
    stream_transactions()