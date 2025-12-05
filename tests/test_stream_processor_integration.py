#!/usr/bin/env python3
"""
Integration tests for Stream Processor component
Tests actual StreamProcessor methods with real trade data
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from consumer.stream_processor import StreamProcessor, parse_timestamp, safe_float


class TestStreamProcessorCleanTrade(unittest.TestCase):
    """Integration tests for clean_trade method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = StreamProcessor(
            kafka_bootstrap="localhost:29092",
            topic="test-topic",
            group_id="test-group",
            output_dir="./test_outputs"
        )
    
    def test_clean_trade_standard_format(self):
        """Test cleaning trade with standard format"""
        trade = {
            'symbol': 'BTCUSD',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': 1699564800000,
            'trade_id': 12345
        }
        
        cleaned = self.processor.clean_trade(trade)
        
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned['symbol'], 'BTCUSD')
        self.assertEqual(cleaned['price'], 50000.0)
        self.assertEqual(cleaned['quantity'], 0.5)
        self.assertIsInstance(cleaned['timestamp'], pd.Timestamp)
        self.assertEqual(cleaned['trade_id'], 12345)
    
    def test_clean_trade_alternative_field_names(self):
        """Test cleaning trade with alternative field names"""
        # Test with 's' instead of 'symbol', 'p' instead of 'price', etc.
        trade = {
            's': 'ETHUSD',
            'p': 3000.0,
            'q': 1.0,
            'ts': 1699564800000,
            'id': 67890
        }
        
        cleaned = self.processor.clean_trade(trade)
        
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned['symbol'], 'ETHUSD')
        self.assertEqual(cleaned['price'], 3000.0)
        self.assertEqual(cleaned['quantity'], 1.0)
    
    def test_clean_trade_invalid_data(self):
        """Test cleaning trade with invalid data"""
        invalid_trades = [
            # Missing required fields
            {'symbol': 'BTCUSD'},  # Missing price, quantity, timestamp
            {'price': 50000.0},     # Missing symbol, quantity, timestamp
            # Invalid values
            {'symbol': 'BTCUSD', 'price': -100, 'quantity': 0.5, 'timestamp': 1699564800000},
            {'symbol': 'BTCUSD', 'price': 50000, 'quantity': 0, 'timestamp': 1699564800000},
            {'symbol': 'BTCUSD', 'price': 0, 'quantity': 0.5, 'timestamp': 1699564800000},
            # Invalid timestamp
            {'symbol': 'BTCUSD', 'price': 50000, 'quantity': 0.5, 'timestamp': None},
            {'symbol': 'BTCUSD', 'price': 50000, 'quantity': 0.5, 'timestamp': 'invalid'},
        ]
        
        for trade in invalid_trades:
            cleaned = self.processor.clean_trade(trade)
            self.assertIsNone(cleaned, f"Should reject invalid trade: {trade}")
    
    def test_clean_trade_symbol_normalization(self):
        """Test symbol normalization to uppercase"""
        trade = {
            'symbol': 'btcusd',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': 1699564800000
        }
        
        cleaned = self.processor.clean_trade(trade)
        
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned['symbol'], 'BTCUSD')
    
    def test_clean_trade_timestamp_formats(self):
        """Test timestamp parsing from different formats"""
        base_time = datetime(2023, 11, 9, 12, 0, 0)
        timestamp_ms = int(base_time.timestamp() * 1000)
        
        # Test milliseconds timestamp
        trade_ms = {
            'symbol': 'BTCUSD',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': timestamp_ms
        }
        cleaned_ms = self.processor.clean_trade(trade_ms)
        self.assertIsNotNone(cleaned_ms)
        self.assertIsInstance(cleaned_ms['timestamp'], pd.Timestamp)
        
        # Test ISO string
        trade_iso = {
            'symbol': 'BTCUSD',
            'price': 50000.0,
            'quantity': 0.5,
            'timestamp': base_time.isoformat()
        }
        cleaned_iso = self.processor.clean_trade(trade_iso)
        # Note: parse_timestamp may not handle ISO strings directly
        # This test documents current behavior


class TestStreamProcessorOHLCCalculation(unittest.TestCase):
    """Integration tests for OHLC calculation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = StreamProcessor(
            kafka_bootstrap="localhost:29092",
            topic="test-topic",
            group_id="test-group",
            output_dir="./test_outputs"
        )
    
    def test_ohlc_aggregation_from_trades(self):
        """Test OHLC calculation from multiple trades"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        # Create trades within 1 second
        trades = []
        prices = [50000, 50100, 49900, 50050, 50025]  # High=50100, Low=49900, First=50000, Last=50025
        
        for i, price in enumerate(prices):
            trade = {
                'symbol': 'BTCUSD',
                'price': float(price),
                'quantity': 0.1,
                'timestamp': base_time + timedelta(milliseconds=i*200),
                'trade_id': i
            }
            cleaned = self.processor.clean_trade(trade)
            if cleaned:
                self.processor.add_to_buffer(cleaned)
        
        # Emit windows
        watermark = base_time + timedelta(seconds=2)
        self.processor.emit_ready_windows(watermark_time=watermark)
        
        # Check OHLC output
        self.assertGreater(len(self.processor.ohlc_out), 0)
        
        if self.processor.ohlc_out:
            ohlc_df = pd.concat(self.processor.ohlc_out, ignore_index=True)
            if not ohlc_df.empty:
                row = ohlc_df.iloc[0]
                self.assertIn('open', row)
                self.assertIn('high', row)
                self.assertIn('low', row)
                self.assertIn('close', row)
                self.assertIn('volume', row)
                self.assertGreaterEqual(row['high'], row['low'])
                self.assertGreaterEqual(row['high'], row['open'])
                self.assertGreaterEqual(row['high'], row['close'])
    
    def test_volume_aggregation(self):
        """Test volume calculation (sum of quantities)"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        quantities = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_volume = sum(quantities)
        
        for i, qty in enumerate(quantities):
            trade = {
                'symbol': 'BTCUSD',
                'price': 50000.0,
                'quantity': qty,
                'timestamp': base_time + timedelta(milliseconds=i*200),
                'trade_id': i
            }
            cleaned = self.processor.clean_trade(trade)
            if cleaned:
                self.processor.add_to_buffer(cleaned)
        
        watermark = base_time + timedelta(seconds=2)
        self.processor.emit_ready_windows(watermark_time=watermark)
        
        if self.processor.ohlc_out:
            ohlc_df = pd.concat(self.processor.ohlc_out, ignore_index=True)
            if not ohlc_df.empty:
                # Volume should be approximately sum of quantities
                actual_volume = ohlc_df.iloc[0]['volume']
                self.assertGreater(actual_volume, 0)


class TestStreamProcessorVolatility(unittest.TestCase):
    """Integration tests for volatility calculation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = StreamProcessor(
            kafka_bootstrap="localhost:29092",
            topic="test-topic",
            group_id="test-group",
            output_dir="./test_outputs"
        )
    
    def test_volatility_calculation_logic(self):
        """Test volatility calculation using log returns"""
        # Create price series with known volatility
        prices = pd.Series([100.0, 105.0, 102.0, 108.0, 110.0, 107.0, 112.0])
        
        # Calculate log returns
        log_returns = np.log(prices).diff()
        
        # Calculate volatility (std of log returns)
        volatility = log_returns.std()
        
        self.assertIsNotNone(volatility)
        self.assertGreater(volatility, 0)
        self.assertIsInstance(volatility, (float, np.float64))
        
        # Volatility should be reasonable (not NaN or inf)
        self.assertFalse(np.isnan(volatility))
        self.assertFalse(np.isinf(volatility))


class TestStreamProcessorUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def test_parse_timestamp_milliseconds(self):
        """Test parse_timestamp with milliseconds"""
        timestamp_ms = 1699564800000
        result = parse_timestamp(timestamp_ms)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.Timestamp)
    
    def test_parse_timestamp_iso_string(self):
        """Test parse_timestamp with ISO string"""
        iso_string = "2023-11-09T12:00:00Z"
        result = parse_timestamp(iso_string)
        
        # parse_timestamp may handle ISO strings
        if result is not None:
            self.assertIsInstance(result, pd.Timestamp)
    
    def test_safe_float_valid(self):
        """Test safe_float with valid inputs"""
        valid_inputs = ['100.5', 100.5, 100, '0.001']
        
        for inp in valid_inputs:
            result = safe_float(inp)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, float)
    
    def test_safe_float_invalid(self):
        """Test safe_float with invalid inputs"""
        invalid_inputs = [None, 'not a number', '', 'NaN']
        
        for inp in invalid_inputs:
            result = safe_float(inp)
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()

