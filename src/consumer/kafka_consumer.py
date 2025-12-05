#!/usr/bin/env python3
"""
Kafka Consumer Stub - Milestone 1
Basic consumer that prints raw trade data.

Note: For full processing (OHLC calculation, volatility, parquet persistence),
use stream_processor.py instead. This consumer is kept for debugging/verification.
"""

import json
import os
import time
import logging
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CryptoConsumer:
    """Basic consumer for cryptocurrency trade data"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'crypto-trades')
        self.group_id = os.getenv('KAFKA_GROUP_ID', 'crypto-consumer-group')
        self.max_poll_records = int(os.getenv('MAX_POLL_RECORDS', '500'))
        
        self.consumer = None
        self.message_count = 0
        self.start_time = time.time()
        
        logger.info(f"Initializing CryptoConsumer")
        logger.info(f"Group ID: {self.group_id}")
        logger.info(f"Max poll records: {self.max_poll_records}")
        
    def connect_kafka(self):
        """Initialize Kafka consumer with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                    max_poll_records=self.max_poll_records
                )
                logger.info("Successfully connected to Kafka")
                return True
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
        return False
    
    def process_message(self, message):
        """
        Process individual message - prints raw data
        
        Note: For full processing capabilities, use stream_processor.py which includes:
        - Data cleaning/preprocessing
        - 1s OHLC calculation (Open, High, Low, Close)
        - Volatility calculation
        - Parquet persistence
        """
        try:
            trade = message.value
            
            self.message_count += 1
            
            # Print raw trade data for verification
            timestamp = datetime.fromtimestamp(trade['timestamp'] / 1000)
            
            print(f"\n{'='*80}")
            print(f"RAW TRADE DATA - Message #{self.message_count}")
            print(f"{'='*80}")
            print(f"Symbol:       {trade['symbol']}")
            print(f"Price:        ${trade['price']:,.2f}")
            print(f"Quantity:     {trade['quantity']:.8f}")
            print(f"Timestamp:    {timestamp.isoformat()}")
            print(f"Trade ID:     {trade['trade_id']}")
            print(f"Buyer Maker:  {trade['is_buyer_maker']}")
            print(f"{'='*80}")
            
            # Log summary every 50 messages
            if self.message_count % 50 == 0:
                elapsed = time.time() - self.start_time
                rate = self.message_count / elapsed
                logger.info(f"Processed {self.message_count} messages | Rate: {rate:.2f} msg/sec")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def start(self):
        """Start consuming messages"""
        logger.info("="*80)
        logger.info("STARTING CRYPTO CONSUMER (STUB)")
        logger.info("This consumer prints raw trade data.")
        logger.info("For full processing, use stream_processor.py instead.")
        
        # Connect to Kafka
        self.connect_kafka()
        
        logger.info(f"Subscribed to topic: {self.topic}")
        logger.info("Waiting for messages...\n")
        
        try:
            for message in self.consumer:
                self.process_message(message)
                
        except KeyboardInterrupt:
            logger.info("\nShutting down consumer...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            # Close consumer
            if self.consumer:
                self.consumer.close()
                logger.info("Consumer closed")


def main():
    """Main entry point"""
    consumer = CryptoConsumer()
    consumer.start()


if __name__ == '__main__':
    main()