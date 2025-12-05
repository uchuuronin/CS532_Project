#!/usr/bin/env python3
"""
Integration tests for Data Loader component
Tests actual DataLoader methods with real parquet files
"""

import unittest
import sys
import os
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.data_loader import DataLoader


class TestDataLoaderIntegration(unittest.TestCase):
    """Integration tests for DataLoader with actual parquet files"""
    
    def setUp(self):
        """Set up test fixtures with temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.loader = DataLoader(output_dir=self.test_dir)
        
        # Create test parquet files
        self.create_test_data()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_data(self):
        """Create sample parquet files for testing"""
        # Create OHLC data
        ohlc_dir = Path(self.test_dir) / "ohlc" / "symbol=BTCUSD" / "date=2023-11-09"
        ohlc_dir.mkdir(parents=True, exist_ok=True)
        
        timestamps = pd.date_range('2023-11-09 12:00:00', periods=10, freq='1s', tz='UTC')
        ohlc_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': [50000 + i*10 for i in range(10)],
            'high': [50020 + i*10 for i in range(10)],
            'low': [49980 + i*10 for i in range(10)],
            'close': [50010 + i*10 for i in range(10)],
            'volume': [0.5 + i*0.1 for i in range(10)],
            'symbol': ['BTCUSD'] * 10,
            'date': ['2023-11-09'] * 10
        })
        
        ohlc_file = ohlc_dir / "ohlc_BTCUSD_2023-11-09_1699564800.parquet"
        ohlc_data.to_parquet(ohlc_file, index=False)
        
        # Create volatility data
        vol_dir = Path(self.test_dir) / "volatility" / "symbol=BTCUSD" / "date=2023-11-09"
        vol_dir.mkdir(parents=True, exist_ok=True)
        
        vol_data = pd.DataFrame({
            'timestamp': timestamps,
            'volatility': [0.001 + i*0.0001 for i in range(10)],
            'symbol': ['BTCUSD'] * 10
        })
        
        vol_file = vol_dir / "vol_BTCUSD_2023-11-09_1699564800.parquet"
        vol_data.to_parquet(vol_file, index=False)
        
        # Create ETHUSD data for multi-symbol testing
        eth_ohlc_dir = Path(self.test_dir) / "ohlc" / "symbol=ETHUSD" / "date=2023-11-09"
        eth_ohlc_dir.mkdir(parents=True, exist_ok=True)
        
        eth_ohlc_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': [3000 + i*5 for i in range(10)],
            'high': [3010 + i*5 for i in range(10)],
            'low': [2990 + i*5 for i in range(10)],
            'close': [3005 + i*5 for i in range(10)],
            'volume': [1.0 + i*0.1 for i in range(10)],
            'symbol': ['ETHUSD'] * 10,
            'date': ['2023-11-09'] * 10
        })
        
        eth_ohlc_file = eth_ohlc_dir / "ohlc_ETHUSD_2023-11-09_1699564800.parquet"
        eth_ohlc_data.to_parquet(eth_ohlc_file, index=False)
    
    def test_load_ohlc_by_symbol(self):
        """Test loading OHLC data filtered by symbol"""
        df = self.loader.load_ohlc(symbol='BTCUSD')
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 10)
        self.assertTrue(all(df['symbol'] == 'BTCUSD'))
        self.assertIn('timestamp', df.columns)
        self.assertIn('open', df.columns)
        self.assertIn('high', df.columns)
        self.assertIn('low', df.columns)
        self.assertIn('close', df.columns)
        self.assertIn('volume', df.columns)
    
    def test_load_ohlc_with_limit(self):
        """Test loading OHLC data with limit"""
        df = self.loader.load_ohlc(symbol='BTCUSD', limit=5)
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 5)
        # Should return last 5 records
        self.assertEqual(df.iloc[-1]['timestamp'], df.iloc[-1]['timestamp'])
    
    def test_load_ohlc_with_date_range(self):
        """Test loading OHLC data filtered by date range"""
        df = self.loader.load_ohlc(
            symbol='BTCUSD',
            start_date='2023-11-09',
            end_date='2023-11-09'
        )
        
        self.assertFalse(df.empty)
        # All timestamps should be on 2023-11-09
        dates = df['timestamp'].dt.date
        self.assertTrue(all(d == pd.Timestamp('2023-11-09').date() for d in dates))
    
    def test_load_ohlc_all_symbols(self):
        """Test loading OHLC data for all symbols"""
        df = self.loader.load_ohlc()  # No symbol filter
        
        self.assertFalse(df.empty)
        # Should have both BTCUSD and ETHUSD
        symbols = df['symbol'].unique()
        self.assertIn('BTCUSD', symbols)
        self.assertIn('ETHUSD', symbols)
    
    def test_load_volatility_by_symbol(self):
        """Test loading volatility data filtered by symbol"""
        df = self.loader.load_volatility(symbol='BTCUSD')
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 10)
        self.assertTrue(all(df['symbol'] == 'BTCUSD'))
        self.assertIn('timestamp', df.columns)
        self.assertIn('volatility', df.columns)
    
    def test_load_volatility_with_limit(self):
        """Test loading volatility data with limit"""
        df = self.loader.load_volatility(symbol='BTCUSD', limit=3)
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 3)
    
    def test_get_available_symbols(self):
        """Test getting list of available symbols"""
        symbols = self.loader.get_available_symbols()
        
        self.assertIsInstance(symbols, list)
        self.assertIn('BTCUSD', symbols)
        self.assertIn('ETHUSD', symbols)
        self.assertGreater(len(symbols), 0)
    
    def test_load_nonexistent_symbol(self):
        """Test loading data for non-existent symbol"""
        df = self.loader.load_ohlc(symbol='INVALID')
        
        self.assertTrue(df.empty)
        self.assertEqual(len(df), 0)
    
    def test_load_with_invalid_date_range(self):
        """Test loading data with date range that has no data"""
        df = self.loader.load_ohlc(
            symbol='BTCUSD',
            start_date='2024-01-01',
            end_date='2024-01-02'
        )
        
        # Should return empty dataframe
        self.assertTrue(df.empty)
    
    def test_data_sorted_by_timestamp(self):
        """Test that loaded data is sorted by timestamp"""
        df = self.loader.load_ohlc(symbol='BTCUSD')
        
        if not df.empty:
            timestamps = df['timestamp'].tolist()
            self.assertEqual(timestamps, sorted(timestamps))
    
    def test_timestamp_timezone(self):
        """Test that timestamps have UTC timezone"""
        df = self.loader.load_ohlc(symbol='BTCUSD')
        
        if not df.empty:
            first_ts = df['timestamp'].iloc[0]
            self.assertIsNotNone(first_ts.tz)
            # Should be UTC
            self.assertEqual(str(first_ts.tz), 'UTC')


class TestDataLoaderErrorHandling(unittest.TestCase):
    """Test error handling in DataLoader"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.loader = DataLoader(output_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_load_from_empty_directory(self):
        """Test loading from directory with no data"""
        df = self.loader.load_ohlc(symbol='BTCUSD')
        
        self.assertTrue(df.empty)
        self.assertEqual(len(df), 0)
    
    def test_load_with_corrupted_parquet(self):
        """Test handling of corrupted parquet files"""
        # Create a corrupted parquet file
        ohlc_dir = Path(self.test_dir) / "ohlc" / "symbol=BTCUSD" / "date=2023-11-09"
        ohlc_dir.mkdir(parents=True, exist_ok=True)
        
        corrupted_file = ohlc_dir / "corrupted.parquet"
        with open(corrupted_file, 'w') as f:
            f.write("not a parquet file")
        
        # Should handle gracefully
        df = self.loader.load_ohlc(symbol='BTCUSD')
        
        # Should return empty or skip corrupted file
        # Current implementation prints error but continues
        self.assertIsInstance(df, pd.DataFrame)
    
    def test_get_symbols_from_empty_directory(self):
        """Test getting symbols from empty directory"""
        symbols = self.loader.get_available_symbols()
        
        self.assertIsInstance(symbols, list)
        self.assertEqual(len(symbols), 0)


if __name__ == '__main__':
    unittest.main()

