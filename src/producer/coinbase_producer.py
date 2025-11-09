#!/usr/bin/env python3
"""
Coinbase WebSocket Producer - Milestone 1
Connects to Coinbase API and streams raw trade data to Kafka.
Coinbase has high volume and no geo-restrictions!
"""

import json
import os
import time
import logging
from datetime import datetime
import websocket
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoinbaseProducer:
    """Producer for streaming Coinbase trade data to Kafka"""
    
    # Map common symbols to Coinbase product IDs
    SYMBOL_MAP = {
        'BTCUSDT': 'BTC-USD',
        'ETHUSDT': 'ETH-USD',
        'USDTUSDT': 'USDT-USD'
    }
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'crypto-trades')
        symbols_env = os.getenv('SYMBOLS', 'BTCUSDT,ETHUSDT,USDTUSDT').split(',')
        
        # Convert to Coinbase product IDs
        self.symbols = [self.SYMBOL_MAP.get(s, s) for s in symbols_env]
        self.batch_size = int(os.getenv('BATCH_SIZE', '1'))
        self.replay_speed = float(os.getenv('REPLAY_SPEED', '1'))
        
        self.producer = None
        self.ws = None
        self.message_count = 0
        self.start_time = time.time()
        
        logger.info(f"Initializing CoinbaseProducer")
        logger.info(f"Symbols: {self.symbols}")
        logger.info(f"Batch size: {self.batch_size}, Replay speed: {self.replay_speed}x")
        
    def connect_kafka(self):
        """Initialize Kafka producer with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                    compression_type='gzip'
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
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Coinbase sends different message types
            if data.get('type') == 'match':
                # Normalize Coinbase trade data to match our format
                trade_data = {
                    'symbol': data['product_id'].replace('-', ''),  # BTC-USD -> BTCUSD
                    'price': float(data['price']),
                    'quantity': float(data['size']),
                    'timestamp': int(datetime.fromisoformat(data['time'].replace('Z', '+00:00')).timestamp() * 1000),
                    'is_buyer_maker': data['side'] == 'sell',  # sell side = buyer is maker
                    'trade_id': data['trade_id']
                }
                
                self.send_to_kafka(trade_data)
                
                # Apply replay speed throttling (for future stress testing)
                if self.replay_speed < 1:
                    time.sleep(1.0 / self.replay_speed)
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def send_to_kafka(self, trade_data):
        """Send trade data to Kafka"""
        try:
            # Use symbol as key for partitioning
            key = trade_data['symbol']
            
            future = self.producer.send(self.topic, key=key, value=trade_data)
            future.get(timeout=10)
            
            self.message_count += 1
            
            # Log progress every 100 messages
            if self.message_count % 100 == 0:
                elapsed = time.time() - self.start_time
                rate = self.message_count / elapsed
                logger.info(f"Sent {self.message_count} messages | Rate: {rate:.2f} msg/sec")
                
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket closure"""
        logger.info(f"WebSocket closed: {close_status_code}")
    
    def on_open(self, ws):
        """Handle WebSocket connection opening"""
        logger.info(f"WebSocket connected!")
        
        # Subscribe to trade channels for all symbols
        subscribe_message = {
            "type": "subscribe",
            "product_ids": self.symbols,
            "channels": ["matches"]
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f" Subscribed to: {', '.join(self.symbols)}")
    
    def start(self):
        """Start the producer"""
        logger.info("="*80)
        logger.info("STARTING COINBASE PRODUCER")
        logger.info("="*80)
        
        # Connect to Kafka
        self.connect_kafka()
        
        # Coinbase WebSocket URL (no geo-restrictions!)
        ws_url = "wss://ws-feed.exchange.coinbase.com"
        
        logger.info(f"Connecting to Coinbase WebSocket...")
        logger.info(f"Streaming: {', '.join(self.symbols)}")
        
        # Run forever with automatic reconnection
        while True:
            try:
                # Create NEW WebSocket connection each time
                websocket.enableTrace(False)
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open
                )
                
                # Run the connection
                self.ws.run_forever()
                
                # If we get here, connection closed
                logger.info("WebSocket disconnected, reconnecting in 5 seconds...")
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("Shutting down producer...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)
        
        # Cleanup
        if self.producer:
            self.producer.flush()
            self.producer.close()


def main():
    """Main entry point"""
    producer = CoinbaseProducer()
    producer.start()


if __name__ == '__main__':
    main()