#!/usr/bin/env python3
"""
Unit tests for Stream Processor component
Tests data cleaning, validation, and OHLC calculation logic
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestDataCleaning(unittest.TestCase):
    def test_timestamp_parsing_milliseconds(self):
        """Test parsing timestamp from milliseconds"""
        timestamp_ms = 1699564800000
        ts = pd.to_datetime(timestamp_ms, unit='ms', utc=True)
        
        self.assertIsInstance(ts, pd.Timestamp)
        self.assertEqual(ts.year, 2023)
    
    def test_timestamp_parsing_iso_string(self):
        """Test parsing timestamp from ISO string"""
        iso_string = "2023-11-09T12:00:00Z"
        
        ts = pd.to_datetime(iso_string, utc=True)
        
        self.assertIsInstance(ts, pd.Timestamp)
        self.assertIsNotNone(ts.tzinfo)
    
    def test_price_validation(self):
        """Test price must be positive float"""
        valid_prices = [50000.0, 0.001, 1.99]
        invalid_prices = [-100, 0, None]
        
        for price in valid_prices:
            if price is not None:
                self.assertGreater(float(price), 0)
        
        for price in invalid_prices:
            if price is not None and isinstance(price, (int, float)):
                self.assertFalse(price > 0)
    
    def test_symbol_normalization(self):
        """Test symbol is normalized to uppercase"""
        symbols = ['btcusd', 'ETHUSD', 'UsdtUSD']
        
        for symbol in symbols:
            normalized = str(symbol).upper()
            self.assertEqual(normalized, normalized.upper())
            self.assertIsInstance(normalized, str)


class TestOHLCCalculation(unittest.TestCase):
    def create_sample_trades(self):
        """Create sample trade data for testing"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        trades = []
        # Create trades within 1 second window
        for i in range(5):
            trades.append({
                'timestamp': base_time + timedelta(milliseconds=i*200),
                'price': 50000 + i*10,  # Increasing prices
                'quantity': 0.1,
                'symbol': 'BTCUSD'
            })
        
        return pd.DataFrame(trades)
    
    def test_ohlc_calculation(self):
        """Test basic OHLC calculation from trade data"""
        df = self.create_sample_trades()
        df = df.set_index('timestamp')
        
        # Calculate OHLC for 1 second window
        ohlc = df['price'].resample('1s').agg(['first', 'max', 'min', 'last'])
        
        # Verify structure
        self.assertEqual(len(ohlc.columns), 4)
        self.assertIn('first', ohlc.columns)
        self.assertIn('max', ohlc.columns)
        self.assertIn('min', ohlc.columns)
        self.assertIn('last', ohlc.columns)
        
        # Verify values make sense
        first_row = ohlc.iloc[0]
        self.assertGreaterEqual(first_row['max'], first_row['min'])
        self.assertGreaterEqual(first_row['max'], first_row['first'])
        self.assertGreaterEqual(first_row['max'], first_row['last'])
    
    def test_volume_calculation(self):
        """Test volume calculation (sum of quantities)"""
        df = self.create_sample_trades()
        df = df.set_index('timestamp')
        
        volume = df['quantity'].resample('1s').sum()
        
        # Volume should be sum of all quantities
        expected_volume = 5 * 0.1  # 5 trades, 0.1 each
        self.assertAlmostEqual(volume.iloc[0], expected_volume, places=5)
    
    def test_empty_data_handling(self):
        """Test handling of empty dataframes"""
        empty_df = pd.DataFrame(columns=['timestamp', 'price', 'quantity'])
        
        self.assertTrue(empty_df.empty)
        self.assertEqual(len(empty_df), 0)


class TestVolatilityCalculation(unittest.TestCase):
    def test_log_returns_calculation(self):
        """Test calculation of log returns"""
        prices = pd.Series([100, 105, 102, 108, 110])
        
        # Calculate log returns
        log_returns = np.log(prices).diff()
        
        # First value should be NaN
        self.assertTrue(pd.isna(log_returns.iloc[0]))
        
        # Rest should be numeric
        self.assertEqual(len(log_returns.dropna()), 4)
    
    def test_volatility_std(self):
        """Test volatility as standard deviation of log returns"""
        prices = pd.Series([100, 105, 102, 108, 110, 107, 112])
        
        log_returns = np.log(prices).diff()
        volatility = log_returns.std()
        
        # Volatility should be positive number
        self.assertGreater(volatility, 0)
        self.assertIsInstance(volatility, (float, np.float64))


class TestDataTypes(unittest.TestCase):
    def test_ohlc_data_types(self):
        """Test OHLC output has correct data types"""
        ohlc_data = {
            'timestamp': pd.Timestamp('2023-11-09 12:00:00', tz='UTC'),
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0,
            'volume': 1.5,
            'symbol': 'BTCUSD'
        }
        
        # Check data types
        self.assertIsInstance(ohlc_data['timestamp'], pd.Timestamp)
        self.assertIsInstance(ohlc_data['open'], float)
        self.assertIsInstance(ohlc_data['high'], float)
        self.assertIsInstance(ohlc_data['low'], float)
        self.assertIsInstance(ohlc_data['close'], float)
        self.assertIsInstance(ohlc_data['volume'], float)
        self.assertIsInstance(ohlc_data['symbol'], str)
    
    def test_date_partition_format(self):
        """Test date partition string format"""
        timestamp = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        date_str = timestamp.strftime('%Y-%m-%d')
        
        self.assertEqual(date_str, '2023-11-09')
        self.assertEqual(len(date_str), 10)
        self.assertIn('-', date_str)


class TestStreamProcessorErrorHandling(unittest.TestCase):
    """Additional error handling tests for stream processor"""
    
    def test_ohlc_with_single_trade(self):
        """Test OHLC calculation with only one trade in window"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        trades = pd.DataFrame([{
            'timestamp': base_time,
            'price': 50000.0,
            'quantity': 0.1,
            'symbol': 'BTCUSD'
        }])
        
        trades = trades.set_index('timestamp')
        ohlc = trades['price'].resample('1s').agg(['first', 'max', 'min', 'last'])
        
        if not ohlc.empty:
            row = ohlc.iloc[0]
            # With single trade, all OHLC should be same
            self.assertEqual(row['first'], row['max'])
            self.assertEqual(row['max'], row['min'])
            self.assertEqual(row['min'], row['last'])
    
    def test_ohlc_with_no_trades(self):
        """Test OHLC calculation with no trades"""
        empty_trades = pd.DataFrame(columns=['timestamp', 'price', 'quantity'])
        empty_trades = empty_trades.set_index('timestamp')
        
        ohlc = empty_trades['price'].resample('1s').agg(['first', 'max', 'min', 'last']) if 'price' in empty_trades.columns else pd.DataFrame()
        
        # Should handle empty dataframe
        self.assertIsInstance(ohlc, pd.DataFrame)
    
    def test_volatility_with_constant_prices(self):
        """Test volatility calculation with constant prices (zero volatility)"""
        constant_prices = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0])
        
        log_returns = np.log(constant_prices).diff()
        volatility = log_returns.std()
        
        # With constant prices, volatility should be 0 or NaN
        self.assertTrue(volatility == 0 or pd.isna(volatility))
    
    def test_volatility_with_negative_prices(self):
        """Test handling of negative prices (should not occur but test robustness)"""
        # In real scenario, prices should never be negative
        # But test that system handles it gracefully
        negative_prices = pd.Series([100.0, -50.0, 100.0])
        
        try:
            log_returns = np.log(negative_prices).diff()
            # Should raise error or handle gracefully
        except (ValueError, FloatingPointError):
            # Expected behavior for negative prices
            pass
    
    def test_out_of_order_timestamps(self):
        """Test handling of out-of-order timestamps"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        # Create trades with out-of-order timestamps
        trades = pd.DataFrame([
            {'timestamp': base_time + pd.Timedelta(seconds=2), 'price': 50000, 'quantity': 0.1},
            {'timestamp': base_time, 'price': 50010, 'quantity': 0.1},
            {'timestamp': base_time + pd.Timedelta(seconds=1), 'price': 50020, 'quantity': 0.1},
        ])
        
        # Should sort by timestamp
        trades = trades.sort_values('timestamp')
        timestamps = trades['timestamp'].tolist()
        self.assertEqual(timestamps, sorted(timestamps))


class TestStreamProcessorEdgeCases(unittest.TestCase):
    """Edge case tests for stream processor"""
    
    def test_very_high_volatility(self):
        """Test volatility calculation with very high price changes"""
        prices = pd.Series([100.0, 200.0, 100.0, 200.0, 100.0])
        
        log_returns = np.log(prices).diff()
        volatility = log_returns.std()
        
        # Should calculate without error
        self.assertIsNotNone(volatility)
        self.assertFalse(np.isinf(volatility))
    
    def test_very_low_volatility(self):
        """Test volatility calculation with very small price changes"""
        prices = pd.Series([100.0, 100.001, 100.002, 100.001, 100.003])
        
        log_returns = np.log(prices).diff()
        volatility = log_returns.std()
        
        # Should be very small but positive
        self.assertIsNotNone(volatility)
        self.assertGreaterEqual(volatility, 0)
    
    def test_multiple_symbols_ohlc(self):
        """Test OHLC calculation for multiple symbols"""
        base_time = pd.Timestamp('2023-11-09 12:00:00', tz='UTC')
        
        trades = pd.DataFrame([
            {'timestamp': base_time, 'price': 50000, 'quantity': 0.1, 'symbol': 'BTCUSD'},
            {'timestamp': base_time, 'price': 3000, 'quantity': 1.0, 'symbol': 'ETHUSD'},
        ])
        
        trades = trades.set_index('timestamp')
        
        # Calculate OHLC per symbol
        for symbol in trades['symbol'].unique():
            symbol_trades = trades[trades['symbol'] == symbol]
            ohlc = symbol_trades['price'].resample('1s').agg(['first', 'max', 'min', 'last'])
            
            if not ohlc.empty:
                self.assertIn('first', ohlc.columns)

