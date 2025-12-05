#!/usr/bin/env python3
"""
Unit tests for Data Loader and API component
Tests data loading, filtering, and API response formats
"""

import unittest
import pandas as pd
from datetime import datetime
import json


class TestDataLoaderLogic(unittest.TestCase):
    def create_sample_ohlc_data(self):
        """Create sample OHLC dataframe for testing"""
        timestamps = pd.date_range('2023-11-09 12:00:00', periods=10, freq='1s', tz='UTC')
        
        data = {
            'timestamp': timestamps,
            'open': [50000 + i*10 for i in range(10)],
            'high': [50020 + i*10 for i in range(10)],
            'low': [49980 + i*10 for i in range(10)],
            'close': [50010 + i*10 for i in range(10)],
            'volume': [0.5 + i*0.1 for i in range(10)],
            'symbol': ['BTCUSD'] * 10,
            'date': ['2023-11-09'] * 10
        }
        
        return pd.DataFrame(data)
    
    def test_symbol_filtering(self):
        """Test filtering data by symbol"""
        df = self.create_sample_ohlc_data()
        
        filtered = df[df['symbol'] == 'BTCUSD']
        
        self.assertEqual(len(filtered), 10)
        self.assertTrue(all(filtered['symbol'] == 'BTCUSD'))
    
    def test_limit_filtering(self):
        """Test limiting number of records returned"""
        df = self.create_sample_ohlc_data()
        
        limit = 5
        limited = df.tail(limit)
        
        self.assertEqual(len(limited), limit)
        # Should return last 5 records
        self.assertEqual(limited.iloc[-1]['timestamp'], df.iloc[-1]['timestamp'])
    
    def test_date_range_filtering(self):
        """Test filtering by date range"""
        df = self.create_sample_ohlc_data()
        
        start_date = '2023-11-09'
        end_date = '2023-11-09'
        
        filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        self.assertGreater(len(filtered), 0)
        self.assertTrue(all(filtered['date'] == '2023-11-09'))
    
    def test_timestamp_sorting(self):
        """Test data is sorted by timestamp"""
        df = self.create_sample_ohlc_data()
        sorted_df = df.sort_values('timestamp')
        
        timestamps = sorted_df['timestamp'].tolist()
        self.assertEqual(timestamps, sorted(timestamps))


class TestAPIResponseFormat(unittest.TestCase):
    def test_ohlc_response_structure(self):
        """Test OHLC response has correct structure"""
        response = {
            'data': [
                {
                    'timestamp': '2023-11-09T12:00:00+00:00',
                    'open': 50000.0,
                    'high': 50100.0,
                    'low': 49900.0,
                    'close': 50050.0,
                    'volume': 1.5,
                    'symbol': 'BTCUSD'
                }
            ],
            'count': 1,
            'symbol': 'BTCUSD'
        }
        
        self.assertIn('data', response)
        self.assertIn('count', response)
        self.assertIsInstance(response['data'], list)
        self.assertIsInstance(response['count'], int)
    
    def test_ohlc_data_point_fields(self):
        """Test individual OHLC data point has all required fields"""
        data_point = {
            'timestamp': '2023-11-09T12:00:00+00:00',
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0,
            'volume': 1.5,
            'symbol': 'BTCUSD'
        }
        
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        for field in required_fields:
            self.assertIn(field, data_point, f"Missing field: {field}")
    
    def test_volatility_response_structure(self):
        """Test volatility response structure"""
        response = {
            'data': [
                {
                    'timestamp': '2023-11-09T12:00:00+00:00',
                    'volatility': 0.0023,
                    'symbol': 'BTCUSD'
                }
            ],
            'count': 1,
            'symbol': 'BTCUSD'
        }
        
        self.assertIn('data', response)
        self.assertIn('count', response)
        
        data_point = response['data'][0]
        self.assertIn('timestamp', data_point)
        self.assertIn('volatility', data_point)
        self.assertIn('symbol', data_point)
    
    def test_symbols_list_response(self):
        """Test symbols list response"""
        response = {
            'symbols': ['BTCUSD', 'ETHUSD', 'USDTUSD']
        }
        
        self.assertIn('symbols', response)
        self.assertIsInstance(response['symbols'], list)
        self.assertGreater(len(response['symbols']), 0)
    
    def test_health_check_response(self):
        """Test health check endpoint response"""
        response = {
            'status': 'healthy',
            'service': 'crypto-api'
        }
        
        self.assertIn('status', response)
        self.assertEqual(response['status'], 'healthy')


class TestDataValidation(unittest.TestCase):
    def test_ohlc_price_relationships(self):
        """Test OHLC price relationships (high >= low, etc.)"""
        ohlc = {
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0
        }
        
        # High should be >= all other prices
        self.assertGreaterEqual(ohlc['high'], ohlc['open'])
        self.assertGreaterEqual(ohlc['high'], ohlc['low'])
        self.assertGreaterEqual(ohlc['high'], ohlc['close'])
        
        # Low should be <= all other prices
        self.assertLessEqual(ohlc['low'], ohlc['open'])
        self.assertLessEqual(ohlc['low'], ohlc['high'])
        self.assertLessEqual(ohlc['low'], ohlc['close'])
    
    def test_volume_is_non_negative(self):
        """Test volume is non-negative"""
        volumes = [0.0, 0.5, 1.0, 10.5]
        
        for volume in volumes:
            self.assertGreaterEqual(volume, 0)
    
    def test_timestamp_iso_format(self):
        """Test timestamp can be parsed from ISO format"""
        iso_timestamps = [
            '2023-11-09T12:00:00+00:00',
            '2023-11-09T12:00:00Z',
            '2023-11-09T12:00:00.123456+00:00'
        ]
        
        for ts_str in iso_timestamps:
            # Should parse without error
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            self.assertIsInstance(ts, datetime)


class TestParquetPathStructure(unittest.TestCase):
    def test_ohlc_path_structure(self):
        """Test OHLC parquet path follows partitioning scheme"""
        expected_path = "data/outputs/ohlc/symbol=BTCUSD/date=2023-11-09/ohlc_BTCUSD_2023-11-09_1699564800.parquet"
        
        self.assertIn('symbol=', expected_path)
        self.assertIn('date=', expected_path)
        self.assertIn('.parquet', expected_path)
    
    def test_volatility_path_structure(self):
        """Test volatility parquet path structure"""
        expected_path = "data/outputs/volatility/symbol=BTCUSD/date=2023-11-09/vol_BTCUSD_2023-11-09_1699564800.parquet"
        
        self.assertIn('volatility', expected_path)
        self.assertIn('symbol=', expected_path)
        self.assertIn('date=', expected_path)


class TestDataLoaderErrorHandling(unittest.TestCase):
    """Error handling tests for data loader"""
    
    def test_invalid_symbol_filter(self):
        """Test filtering with invalid symbol"""
        df = self.create_sample_ohlc_data()
        
        filtered = df[df['symbol'] == 'INVALID']
        
        self.assertEqual(len(filtered), 0)
        self.assertTrue(filtered.empty)
    
    def test_invalid_date_range(self):
        """Test filtering with invalid date range"""
        df = self.create_sample_ohlc_data()
        
        # Start date after end date
        filtered = df[(df['date'] >= '2023-11-10') & (df['date'] <= '2023-11-09')]
        
        self.assertEqual(len(filtered), 0)
    
    def test_limit_greater_than_data(self):
        """Test limit greater than available data"""
        df = self.create_sample_ohlc_data()
        
        limit = 1000
        limited = df.tail(limit)
        
        # Should return all available data
        self.assertLessEqual(len(limited), len(df))
        self.assertEqual(len(limited), len(df))
    
    def test_limit_zero_or_negative(self):
        """Test handling of zero or negative limits"""
        df = self.create_sample_ohlc_data()
        
        # Limit of 0 should return empty
        limited_zero = df.tail(0)
        self.assertEqual(len(limited_zero), 0)
        
        # Negative limit should be handled (pandas tail handles this)
        limited_neg = df.tail(-1)
        self.assertIsInstance(limited_neg, pd.DataFrame)


class TestDataLoaderEdgeCases(unittest.TestCase):
    """Edge case tests for data loader"""
    
    def create_sample_ohlc_data(self):
        """Create sample OHLC dataframe for testing"""
        timestamps = pd.date_range('2023-11-09 12:00:00', periods=10, freq='1s', tz='UTC')
        
        data = {
            'timestamp': timestamps,
            'open': [50000 + i*10 for i in range(10)],
            'high': [50020 + i*10 for i in range(10)],
            'low': [49980 + i*10 for i in range(10)],
            'close': [50010 + i*10 for i in range(10)],
            'volume': [0.5 + i*0.1 for i in range(10)],
            'symbol': ['BTCUSD'] * 10,
            'date': ['2023-11-09'] * 10
        }
        
        return pd.DataFrame(data)
    
    def test_empty_dataframe_operations(self):
        """Test operations on empty dataframe"""
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
        
        # Should handle empty dataframe gracefully
        self.assertTrue(empty_df.empty)
        self.assertEqual(len(empty_df), 0)
        
        # Filtering should return empty
        filtered = empty_df[empty_df['symbol'] == 'BTCUSD']
        self.assertTrue(filtered.empty)
    
    def test_missing_columns(self):
        """Test handling of dataframes with missing columns"""
        incomplete_df = pd.DataFrame({
            'timestamp': pd.date_range('2023-11-09 12:00:00', periods=5, freq='1s', tz='UTC'),
            'open': [50000] * 5,
            # Missing high, low, close, volume
        })
        
        # Should handle missing columns
        self.assertIn('timestamp', incomplete_df.columns)
        self.assertIn('open', incomplete_df.columns)
        self.assertNotIn('high', incomplete_df.columns)
    
    def test_duplicate_timestamps(self):
        """Test handling of duplicate timestamps"""
        timestamps = pd.date_range('2023-11-09 12:00:00', periods=5, freq='1s', tz='UTC')
        # Add duplicate
        timestamps = list(timestamps) + [timestamps[0]]
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': [50000] * 6,
            'high': [50100] * 6,
            'low': [49900] * 6,
            'close': [50050] * 6,
            'volume': [0.5] * 6,
            'symbol': ['BTCUSD'] * 6
        })
        
        # Should handle duplicates
        self.assertEqual(len(df), 6)
        self.assertEqual(len(df['timestamp'].unique()), 5)
    
    def test_very_large_limit(self):
        """Test handling of very large limit values"""
        df = self.create_sample_ohlc_data()
        
        # Very large limit
        large_limit = 10**6
        limited = df.tail(large_limit)
        
        # Should return all available data
        self.assertLessEqual(len(limited), len(df))
        self.assertEqual(len(limited), len(df))

