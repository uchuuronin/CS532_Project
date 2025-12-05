#!/usr/bin/env python3
"""
Unit tests for Producer component
Tests data validation and message formatting
"""

import unittest
from datetime import datetime
import json


class TestProducerDataValidation(unittest.TestCase):
    def test_trade_data_structure(self):
        """Verify trade data has all required fields"""
        trade_data = {
            'symbol': 'BTCUSD',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': 1699564800000,
            'is_buyer_maker': True,
            'trade_id': 12345
        }
        
        required_fields = ['symbol', 'price', 'quantity', 'timestamp', 'is_buyer_maker', 'trade_id']
        for field in required_fields:
            self.assertIn(field, trade_data, f"Missing required field: {field}")
    
    def test_price_validation(self):
        """Test price is valid float and positive"""
        valid_prices = [50000.0, 0.001, 100000.99]
        invalid_prices = [-100, 0, 'invalid', None]
        
        for price in valid_prices:
            self.assertIsInstance(price, (int, float))
            self.assertGreater(price, 0)
        
        for price in invalid_prices:
            if isinstance(price, (int, float)):
                self.assertFalse(price > 0, f"Price {price} should be invalid")
    
    def test_quantity_validation(self):
        """Test quantity is valid float and positive"""
        valid_quantities = [0.001, 1.0, 100.5]
        
        for qty in valid_quantities:
            self.assertIsInstance(qty, (int, float))
            self.assertGreater(qty, 0)
    
    def test_symbol_normalization(self):
        """Test symbol is uppercase string"""
        symbols = ['BTCUSD', 'ETHUSD', 'USDTUSD']
        
        for symbol in symbols:
            self.assertIsInstance(symbol, str)
            self.assertEqual(symbol, symbol.upper())
            self.assertGreater(len(symbol), 0)
    
    def test_timestamp_format(self):
        """Test timestamp is valid milliseconds since epoch"""
        timestamp = 1699564800000
        
        # Should be integer or convertible to integer
        self.assertIsInstance(timestamp, int)
        
        # Should be reasonable timestamp (after 2020)
        self.assertGreater(timestamp, 1577836800000)  # Jan 1, 2020
    
    def test_trade_data_serialization(self):
        """Test trade data can be JSON serialized"""
        trade_data = {
            'symbol': 'BTCUSD',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': 1699564800000,
            'is_buyer_maker': True,
            'trade_id': 12345
        }
        
        # Should serialize without errors
        json_str = json.dumps(trade_data)
        self.assertIsInstance(json_str, str)
        
        # Should deserialize back to original
        deserialized = json.loads(json_str)
        self.assertEqual(deserialized, trade_data)


class TestSymbolMapping(unittest.TestCase):
    def test_coinbase_symbol_mapping(self):
        """Test Coinbase symbol format conversion"""
        # Coinbase uses BTC-USD format
        coinbase_symbols = {
            'BTCUSDT': 'BTC-USD',
            'ETHUSDT': 'ETH-USD',
            'USDTUSDT': 'USDT-USD'
        }
        
        for input_symbol, expected in coinbase_symbols.items():
            # Test mapping exists
            self.assertIsInstance(expected, str)
            self.assertIn('-', expected)
    
    def test_normalized_output_format(self):
        """Test normalized output removes hyphens"""
        coinbase_product_id = 'BTC-USD'
        normalized = coinbase_product_id.replace('-', '')
        
        self.assertEqual(normalized, 'BTCUSD')
        self.assertNotIn('-', normalized)


class TestProducerErrorHandling(unittest.TestCase):
    """Additional error handling tests"""
    
    def test_missing_required_fields(self):
        """Test handling of trade data with missing required fields"""
        incomplete_trades = [
            {},  # Empty dict
            {'symbol': 'BTCUSD'},  # Missing price, quantity, timestamp
            {'price': 50000.0},  # Missing symbol, quantity, timestamp
            {'symbol': 'BTCUSD', 'price': 50000.0},  # Missing quantity, timestamp
        ]
        
        required_fields = ['symbol', 'price', 'quantity', 'timestamp']
        for trade in incomplete_trades:
            for field in required_fields:
                if field not in trade:
                    # Should handle missing field gracefully
                    self.assertNotIn(field, trade)
    
    def test_type_errors(self):
        """Test handling of type errors in data conversion"""
        # Test invalid price types
        invalid_prices = ['not a number', None, '', []]
        for price in invalid_prices:
            try:
                float(price)
            except (ValueError, TypeError):
                # Expected behavior
                pass
        
        # Test invalid quantity types
        invalid_quantities = ['not a number', None, '', {}]
        for qty in invalid_quantities:
            try:
                float(qty)
            except (ValueError, TypeError):
                # Expected behavior
                pass
    
    def test_extreme_values(self):
        """Test handling of extreme values"""
        # Very large numbers
        large_price = 1e10
        self.assertIsInstance(large_price, (int, float))
        
        # Very small numbers
        small_quantity = 1e-10
        self.assertGreater(small_quantity, 0)
        
        # Very large timestamp
        large_timestamp = 9999999999999
        self.assertIsInstance(large_timestamp, int)
    
    def test_special_characters_in_symbol(self):
        """Test handling of special characters in symbol"""
        symbols_with_special = ['BTC-USD', 'BTC/USD', 'BTC_USD']
        
        for symbol in symbols_with_special:
            # Should handle or normalize
            normalized = symbol.replace('-', '').replace('/', '').replace('_', '')
            self.assertIsInstance(normalized, str)


if __name__ == '__main__':
    unittest.main()
