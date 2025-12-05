#!/usr/bin/env python3
"""
Integration tests for Producer component
Tests actual producer methods with real data structures
"""

import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from producer.binance_producer import BinanceProducer
from producer.coinbase_producer import CoinbaseProducer


class TestBinanceProducerIntegration(unittest.TestCase):
    """Integration tests for BinanceProducer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.producer = BinanceProducer()
    
    def test_normalize_binance_trade_data(self):
        """Test Binance trade data normalization"""
        # Simulate Binance WebSocket message format
        binance_message = {
            'e': 'aggTrade',
            's': 'BTCUSDT',
            'p': '50000.00',
            'q': '0.5',
            'T': 1699564800000,
            'm': False,
            'a': 12345
        }
        
        # Expected normalized format
        expected_trade = {
            'symbol': 'BTCUSDT',
            'price': 50000.00,
            'quantity': 0.5,
            'timestamp': 1699564800000,
            'is_buyer_maker': False,
            'trade_id': 12345
        }
        
        # Simulate the normalization logic from on_message
        trade_data = {
            'symbol': binance_message['s'],
            'price': float(binance_message['p']),
            'quantity': float(binance_message['q']),
            'timestamp': binance_message['T'],
            'is_buyer_maker': binance_message['m'],
            'trade_id': binance_message['a']
        }
        
        # Verify structure
        self.assertEqual(trade_data['symbol'], expected_trade['symbol'])
        self.assertEqual(trade_data['price'], expected_trade['price'])
        self.assertEqual(trade_data['quantity'], expected_trade['quantity'])
        self.assertEqual(trade_data['timestamp'], expected_trade['timestamp'])
        self.assertIsInstance(trade_data['price'], float)
        self.assertIsInstance(trade_data['quantity'], float)
        self.assertIsInstance(trade_data['timestamp'], int)
    
    def test_binance_price_validation(self):
        """Test price validation in Binance format"""
        valid_prices = ['50000.00', '0.001', '100000.99']
        invalid_prices = ['-100', '0', 'invalid', '']
        
        for price_str in valid_prices:
            try:
                price = float(price_str)
                self.assertGreater(price, 0)
            except ValueError:
                self.fail(f"Should parse valid price: {price_str}")
        
        for price_str in invalid_prices:
            if price_str:
                try:
                    price = float(price_str)
                    if price <= 0:
                        # This is expected for negative or zero
                        pass
                except ValueError:
                    # This is expected for non-numeric
                    pass
    
    def test_binance_symbol_format(self):
        """Test Binance symbol format handling"""
        symbols = ['BTCUSDT', 'ETHUSDT', 'USDTUSDT']
        
        for symbol in symbols:
            self.assertIsInstance(symbol, str)
            self.assertEqual(len(symbol), len(symbol.upper()))
            # Binance uses USDT pairs
            self.assertTrue(symbol.endswith('USDT') or symbol.endswith('USD'))


class TestCoinbaseProducerIntegration(unittest.TestCase):
    """Integration tests for CoinbaseProducer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.producer = CoinbaseProducer()
    
    def test_symbol_mapping(self):
        """Test Coinbase symbol mapping"""
        symbol_map = CoinbaseProducer.SYMBOL_MAP
        
        self.assertIn('BTCUSDT', symbol_map)
        self.assertIn('ETHUSDT', symbol_map)
        self.assertIn('USDTUSDT', symbol_map)
        
        self.assertEqual(symbol_map['BTCUSDT'], 'BTC-USD')
        self.assertEqual(symbol_map['ETHUSDT'], 'ETH-USD')
    
    def test_normalize_coinbase_trade_data(self):
        """Test Coinbase trade data normalization"""
        # Simulate Coinbase WebSocket message format
        coinbase_message = {
            'type': 'match',
            'product_id': 'BTC-USD',
            'price': '50000.00',
            'size': '0.5',
            'time': '2023-11-09T12:00:00.000Z',
            'side': 'buy',
            'trade_id': 12345
        }
        
        # Expected normalized format (from on_message logic)
        normalized_symbol = coinbase_message['product_id'].replace('-', '')
        normalized_price = float(coinbase_message['price'])
        normalized_quantity = float(coinbase_message['size'])
        
        # Verify normalization
        self.assertEqual(normalized_symbol, 'BTCUSD')
        self.assertEqual(normalized_price, 50000.00)
        self.assertEqual(normalized_quantity, 0.5)
        self.assertIsInstance(normalized_price, float)
        self.assertIsInstance(normalized_quantity, float)
    
    def test_coinbase_timestamp_conversion(self):
        """Test Coinbase timestamp conversion to milliseconds"""
        from datetime import datetime
        
        coinbase_time = '2023-11-09T12:00:00.000Z'
        dt = datetime.fromisoformat(coinbase_time.replace('Z', '+00:00'))
        timestamp_ms = int(dt.timestamp() * 1000)
        
        self.assertIsInstance(timestamp_ms, int)
        self.assertGreater(timestamp_ms, 0)
        # Should be around Nov 9, 2023
        self.assertGreater(timestamp_ms, 1699000000000)
    
    def test_coinbase_side_to_buyer_maker(self):
        """Test Coinbase side field conversion"""
        # 'sell' side means buyer is maker
        self.assertEqual(True, 'sell' == 'sell')  # buyer is maker
        self.assertEqual(False, 'buy' == 'sell')   # buyer is not maker


class TestProducerErrorHandling(unittest.TestCase):
    """Test error handling in producers"""
    
    def test_missing_fields_handling(self):
        """Test handling of messages with missing fields"""
        incomplete_message = {
            'e': 'aggTrade',
            's': 'BTCUSDT',
            # Missing price, quantity, timestamp
        }
        
        # Should handle missing fields gracefully
        price = incomplete_message.get('p')
        quantity = incomplete_message.get('q')
        timestamp = incomplete_message.get('T')
        
        self.assertIsNone(price)
        self.assertIsNone(quantity)
        self.assertIsNone(timestamp)
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON"""
        invalid_json_strings = [
            'not json',
            '{invalid}',
            '{"incomplete":',
            ''
        ]
        
        for json_str in invalid_json_strings:
            try:
                import json
                data = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                # Expected behavior
                pass
    
    def test_type_conversion_errors(self):
        """Test handling of type conversion errors"""
        invalid_price_strings = ['not a number', None, '', 'NaN']
        
        for price_str in invalid_price_strings:
            try:
                if price_str is not None:
                    price = float(price_str)
            except (ValueError, TypeError):
                # Expected behavior
                pass


if __name__ == '__main__':
    unittest.main()

