#!/usr/bin/env python3
"""
Load Testing for FastAPI Endpoints using Locust
Tests concurrent client access to API endpoints

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    
Then open http://localhost:8089 and configure:
    - Number of users: 10, 100, 1000
    - Spawn rate: 10 users/sec
    - Host: http://localhost:8000
"""

from locust import HttpUser, task, between, LoadTestShape
import random


class CryptoAPIUser(HttpUser):
    """
    Simulates a user accessing the cryptocurrency API
    """
    # Wait 1-5 seconds between requests
    wait_time = between(1, 5)
    
    # Available symbols for testing
    symbols = ['BTCUSD', 'ETHUSD', 'USDTUSD']
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Check if API is healthy
        self.client.get("/health")
    
    @task(5)
    def get_ohlc_data(self):
        """Get OHLC data - most common operation (weight=5)"""
        symbol = random.choice(self.symbols)
        limit = random.choice([100, 500, 1000])
        
        self.client.get(
            f"/api/ohlc/",
            params={'symbol': symbol, 'limit': limit},
            name="/api/ohlc/ [symbol+limit]"
        )
    
    @task(3)
    def get_volatility_data(self):
        """Get volatility data (weight=3)"""
        symbol = random.choice(self.symbols)
        limit = random.choice([100, 500, 1000])
        
        self.client.get(
            f"/api/volatility/",
            params={'symbol': symbol, 'limit': limit},
            name="/api/volatility/ [symbol+limit]"
        )
    
    @task(2)
    def get_latest_ohlc(self):
        """Get latest OHLC data point (weight=2)"""
        symbol = random.choice(self.symbols)
        
        self.client.get(
            f"/api/ohlc/latest",
            params={'symbol': symbol},
            name="/api/ohlc/latest [symbol]"
        )
    
    @task(4)
    def get_candlestick_chart(self):
        """Get candlestick visualization (weight=4)"""
        symbol = random.choice(self.symbols)
        limit = random.choice([500, 1000])
        
        self.client.get(
            f"/api/viz/candlestick",
            params={'symbol': symbol, 'limit': limit},
            name="/api/viz/candlestick [symbol+limit]"
        )
    
    @task(2)
    def get_price_line_chart(self):
        """Get price line chart (weight=2)"""
        symbol = random.choice(self.symbols)
        limit = random.choice([500, 1000])
        
        self.client.get(
            f"/api/viz/price-line",
            params={'symbol': symbol, 'limit': limit},
            name="/api/viz/price-line [symbol+limit]"
        )
    
    @task(2)
    def get_volatility_chart(self):
        """Get volatility chart (weight=2)"""
        symbol = random.choice(self.symbols)
        limit = random.choice([500, 1000])
        
        self.client.get(
            f"/api/viz/volatility",
            params={'symbol': symbol, 'limit': limit},
            name="/api/viz/volatility [symbol+limit]"
        )
    
    @task(1)
    def get_multi_symbol_chart(self):
        """Get multi-symbol comparison (weight=1)"""
        symbols = ','.join(random.sample(self.symbols, k=random.randint(2, 3)))
        limit = random.choice([500, 1000])
        
        self.client.get(
            f"/api/viz/multi-symbol",
            params={'symbols': symbols, 'limit': limit},
            name="/api/viz/multi-symbol [symbols+limit]"
        )
    
    @task(1)
    def get_symbols_list(self):
        """Get available symbols (weight=1)"""
        self.client.get("/api/symbols", name="/api/symbols")
    
    @task(1)
    def health_check(self):
        """Health check endpoint (weight=1)"""
        self.client.get("/health", name="/health")


class HeavyAPIUser(HttpUser):
    """
    Simulates a heavy user that requests large amounts of data
    """
    
    wait_time = between(2, 8)
    symbols = ['BTCUSD', 'ETHUSD', 'USDTUSD']
    
    @task(3)
    def get_large_ohlc_dataset(self):
        """Request large OHLC dataset"""
        symbol = random.choice(self.symbols)
        
        self.client.get(
            f"/api/ohlc/",
            params={'symbol': symbol, 'limit': 5000},
            name="/api/ohlc/ [large-limit=5000]"
        )
    
    @task(2)
    def get_large_volatility_dataset(self):
        """Request large volatility dataset"""
        symbol = random.choice(self.symbols)
        
        self.client.get(
            f"/api/volatility/",
            params={'symbol': symbol, 'limit': 5000},
            name="/api/volatility/ [large-limit=5000]"
        )
    
    @task(1)
    def get_all_symbols_data(self):
        """Request data for all symbols"""
        # Request without symbol filter returns all
        self.client.get(
            f"/api/ohlc/",
            params={'limit': 1000},
            name="/api/ohlc/ [all-symbols]"
        )


class DashboardUser(HttpUser):
    """
    Simulates a user interacting with the dashboard
    """
    wait_time = between(5, 15)  # Longer wait times (users viewing charts)
    symbols = ['BTCUSD', 'ETHUSD', 'USDTUSD']
    
    def on_start(self):
        """Load dashboard page"""
        self.client.get("/", name="/ [dashboard]")
    
    @task
    def interact_with_dashboard(self):
        """Simulate dashboard interaction"""
        symbol = random.choice(self.symbols)
        chart_type = random.choice(['candlestick', 'price-line', 'volatility', 'volume'])
        
        # Simulate user selecting different chart
        self.client.get(
            f"/api/viz/{chart_type}",
            params={'symbol': symbol, 'limit': 500},
            name=f"/api/viz/{chart_type} [dashboard]"
        )



class StepLoadShape(LoadTestShape):
    """
    A step load shape that increases users in stages
    """
    
    step_time = 120  # 2 minutes per step
    step_users = [10, 50, 100, 200] # users at each step
    spawn_rate = 10
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Calculate current step
        current_step = int(run_time // self.step_time)
        
        # Stop test after all steps complete
        if current_step >= len(self.step_users):
            return None
        
        return (self.step_users[current_step], self.spawn_rate)


class SpikeLoadShape(LoadTestShape):
    """
    A spike load shape for testing sudden traffic increases
    
    Baseline: 10 users for 1 minute
    Spike: 500 users for 30 seconds
    Recovery: 10 users for 1 minute
    """
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 60:
            return (10, 5)
        elif run_time < 90:
            return (500, 50)
        elif run_time < 150:
            return (10, 10)
        else:
            return None
