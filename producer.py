import json
import random
import time
import uuid
from confluent_kafka import Producer

# Kafka broker configuration (adjust if running outside Docker on 'localhost:9092')
KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092'  
}

TOPIC = 'transactions'

def delivery_report(err, msg):
    """ Callback triggered when a message is successfully delivered or fails. """
    if err is not None:
        print(f"❌ Message delivery failed: {err}")
    else:
        print(f"⚡ Event sent to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

def generate_transaction():
    """ Generates a single synthetic bank/financial transaction payload. """
    accounts = [f"ACC_{i:04d}" for i in range(1, 21)]  # Generates ACC_0001 to ACC_0020
    
    sender = random.choice(accounts)
    receiver = random.choice([acc for acc in accounts if acc != sender])
    
    payload = {
        "transaction_id": str(uuid.uuid4())[:8],
        "sender": sender,
        "receiver": receiver,
        "amount": round(random.uniform(10.0, 5000.0), 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return payload

def main():
    producer = Producer(KAFKA_CONFIG)
    print(f"🚀 Producer initialized. Sending messages to topic '{TOPIC}'...\nPress Ctrl+C to stop.\n")

    try:
        while True:
            tx_data = generate_transaction()
            json_payload = json.dumps(tx_data).encode('utf-8')

            # Produce message asynchronously
            producer.produce(
                topic=TOPIC,
                value=json_payload,
                callback=delivery_report
            )

            # Serve delivery callbacks from previous requests
            producer.poll(0)

            # Throttle output: sends 1 transaction per second
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        print("Flushing remaining messages...")
        producer.flush()
        print("Producer stopped successfully.")

if __name__ == '__main__':
    main()