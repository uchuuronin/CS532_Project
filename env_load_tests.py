#!/usr/bin/env python3
"""
Automated Load Testing Script
Runs different configurations and collects performance metrics
"""

import subprocess
import time
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import signal
import pandas as pd
import argparse

class LoadTester:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.results = []
        self.current_process = None
        
    def update_env(self, **kwargs):
        """Update .env file with new values"""
        print(f"Updating configuration: {kwargs}")
        
        # Read current .env
        with open(self.env_file, 'r') as f:
            lines = f.readlines()
        
        # Update values
        updated_lines = []
        for line in lines:
            updated = False
            for key, value in kwargs.items():
                if line.startswith(f"{key}="):
                    updated_lines.append(f"{key}={value}\n")
                    updated = True
                    break
            if not updated:
                updated_lines.append(line)
        
        # Write back
        with open(self.env_file, 'w') as f:
            f.writelines(updated_lines)
        
        print("Configuration updated")
    
    def restart_docker(self):
        """Restart Docker compose services"""
        print("Restarting Docker services...")
        
        # Stop services
        subprocess.run(["docker-compose", "down", "-v"], 
                      cwd=self.project_root, 
                      stdout=subprocess.DEVNULL)
        time.sleep(5)
        
        # Start services
        result = subprocess.run(["docker-compose", "up", "-d"], 
                               cwd=self.project_root,
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error starting Docker: {result.stderr}")
            return False
        
        # Wait for services to be ready
        print("Waiting for services to be ready...")
        time.sleep(30)
        
        return True
    
    def run_consumer(self, duration_sec=120):
        print(f"Running consumer for {duration_sec} seconds...")
        
        env = os.environ.copy()
        env['KAFKA_BOOTSTRAP'] = 'localhost:29092'
        env['KAFKA_TOPIC'] = 'crypto-trades'
        env['OUTPUT_DIR'] = str(self.project_root / 'data' / 'outputs')
        
        consumer_script = self.project_root / 'src' / 'consumer' / 'stream_processor.py'
        
        start_time = time.time()
        
        try:
            self.current_process = subprocess.Popen(
                [sys.executable, str(consumer_script)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for duration
            time.sleep(duration_sec)
            
            # Stop consumer
            self.current_process.send_signal(signal.SIGINT)
            self.current_process.wait(timeout=10)
            
        except subprocess.TimeoutExpired:
            self.current_process.kill()
        except Exception as e:
            print(f"Error running consumer: {e}")
            if self.current_process:
                self.current_process.kill()
            return None
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        }
    
    def collect_metrics(self, config, execution_time):
        print("Collecting metrics...")
        
        metrics = {
            'config': config,
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time
        }
        
        # Count output files
        output_dir = self.project_root / 'data' / 'outputs'
        
        ohlc_files = list((output_dir / 'ohlc').rglob('*.parquet'))
        vol_files = list((output_dir / 'volatility').rglob('*.parquet'))
        
        metrics['files'] = {
            'ohlc_count': len(ohlc_files),
            'volatility_count': len(vol_files)
        }
        
        # Try to count records (requires pandas)
        try:
            
            total_ohlc = 0
            for f in ohlc_files:
                try:
                    df = pd.read_parquet(f)
                    total_ohlc += len(df)
                except:
                    pass
            
            metrics['records'] = {
                'ohlc_total': total_ohlc,
                'throughput': total_ohlc / execution_time['duration'] if execution_time else 0
            }
        except ImportError:
            print("Warning: pandas not available, skipping record count")
        
        # Get Kafka consumer lag
        try:
            result = subprocess.run(
                [
                    "docker", "exec", "kafka", "kafka-consumer-groups",
                    "--bootstrap-server", "localhost:9092",
                    "--describe",
                    "--group", "stream-processor-group"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse lag from output
                for line in result.stdout.split('\n'):
                    if 'LAG' in line or 'crypto-trades' in line:
                        metrics['kafka_lag'] = line
                        break
        except Exception as e:
            print(f"Could not get Kafka lag: {e}")
        
        return metrics
    
    def run_scenario(self, name, symbols, batch_size, partitions, replay_speed, duration=120):
        print(f"Running Case: {name}")
        
        config = {
            'name': name,
            'symbols': symbols,
            'batch_size': batch_size,
            'partitions': partitions,
            'replay_speed': replay_speed
        }
        
        # Update configuration
        self.update_env(
            SYMBOLS=symbols,
            BATCH_SIZE=str(batch_size),
            KAFKA_PARTITIONS=str(partitions),
            REPLAY_SPEED=str(replay_speed)
        )
        
        # Restart Docker
        if not self.restart_docker():
            print("Failed to restart Docker, skipping scenario")
            return None
        
        # Run consumer
        execution_time = self.run_consumer(duration_sec=duration)
        
        if not execution_time:
            print("Failed to run consumer, skipping scenario")
            return None
        
        # Collect metrics
        metrics = self.collect_metrics(config, execution_time)
        
        self.results.append(metrics)
        
        print(f"\nScenario '{name}' completed")
        print(f"Duration: {execution_time['duration']:.1f}s")
        if 'records' in metrics:
            print(f"OHLC records: {metrics['records']['ohlc_total']}")
            print(f"Throughput: {metrics['records']['throughput']:.2f} records/sec")
        
        return metrics
    
    def save_results(self):
        """Save all results to JSON file"""
        results_file = self.project_root / f"load_test_results_{int(time.time())}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Print summary
        for result in self.results:
            config = result['config']
            print(f"\n{config['name']}:")
            print(f"\tConfig: {config['symbols']}, batch={config['batch_size']}, "
                  f"partitions={config['partitions']}, speed={config['replay_speed']}x")
            if 'records' in result:
                print(f"\tRecords: {result['records']['ohlc_total']}")
                print(f"\tThroughput: {result['records']['throughput']:.2f} records/sec")
            if 'files' in result:
                print(f"\tFiles: {result['files']['ohlc_count']} OHLC, "
                      f"{result['files']['volatility_count']} volatility")
    
    def run_all_scenarios(self):
        """Run all predefined test scenarios"""
        scenarios = [
            # (name, symbols, batch_size, partitions, replay_speed, duration)
            ("Baseline-1symbol", "BTCUSDT", 1, 1, 1, 120),
            ("Load-3symbols", "BTCUSDT,ETHUSDT,USDTUSDT", 1, 4, 1, 120),
            ("Batched-Processing", "BTCUSDT,ETHUSDT,USDTUSDT", 32, 4, 1, 120),
            ("Stress-5x", "BTCUSDT,ETHUSDT,USDTUSDT", 32, 4, 5, 120),
            ("Baseline-4partitions", "BTCUSDT", 1, 4, 1, 120),
        ]
        
        print("Starting automated load testing...")
        print(f"Will run {len(scenarios)} cases")
        
        for scenario in scenarios:
            self.run_scenario(*scenario)
            print("Waiting 10 seconds before next scenario...")
            time.sleep(10)
        
        self.save_results()


def main():
    parser = argparse.ArgumentParser(description="Run load tests on crypto pipeline")
    parser.add_argument('--scenario', choices=['all', 'baseline', 'load', 'batched', 'stress'],
                       default='all', help='Which scenario to run')
    parser.add_argument('--duration', type=int, default=120,
                       help='Duration of each test in seconds (default: 120)')
    
    args = parser.parse_args()
    
    tester = LoadTester()
    
    if args.scenario == 'all':
        tester.run_all_scenarios()
    
    elif args.scenario == 'baseline':
        tester.run_scenario("Baseline", "BTCUSDT", 1, 1, 1, args.duration)
        tester.save_results()
    
    elif args.scenario == 'load':
        tester.run_scenario("Load", "BTCUSDT,ETHUSDT,USDTUSDT", 1, 4, 1, args.duration)
        tester.save_results()
    
    elif args.scenario == 'batched':
        tester.run_scenario("Batched", "BTCUSDT,ETHUSDT,USDTUSDT", 32, 4, 1, args.duration)
        tester.save_results()
    
    elif args.scenario == 'stress':
        tester.run_scenario("Stress", "BTCUSDT,ETHUSDT,USDTUSDT", 32, 4, 5, args.duration)
        tester.save_results()
    
    print("\nLoad testing complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nLoad testing interrupted by user")
        sys.exit(0)
