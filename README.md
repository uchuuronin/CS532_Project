# Cryptocurrency Data Realtime Streaming

**Course:** Systems for Data Science  
Cryptocurrency markets are highly dynamic and produce high-velocity data streams, making them an ideal domain for studying distributed streaming systems. This project focuses on building a real-time analytics pipeline for cryptocurrency (like Bitcoin) that emphasizes system design, scalability, and fault tolerance. We further plan to evaluate the pipeline’s latency, throughput, scalability, and recovery time under load testing to assess its fault tolerance and performance.

We want to focus on the  following systems concepts: concurrent I/O vs. CPU stages, bounded queues/backpressure, offset management, configurable consumer parallelism and batching, checkpoint-based recovery and scalable consumer parallelism.

## Architecture

```
   Coinbase WebSocket API
         ↓
   Producer (Python)
         ↓
   Kafka (4 partitions)
         ↓
   Consumer Stub (prints raw data)
```

## SetUp

### Start the Docker env

```bash
docker-compose up -d
```

### Watch Raw Data Being Processed

```bash
docker-compose logs -f consumer
```

You'll see output like:

```
RAW TRADE DATA - Message #123
Symbol:       BTCUSDT
Price:        $42,150.50
Quantity:     0.05234000
Timestamp:    2025-11-09T15:30:45.123000
Trade ID:     12345678
Buyer Maker:  False
```

### Check Producer is Streaming

```bash
docker-compose logs -f producer
```

### Verify Kafka Topics

```bash
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

## Shut down
```bash
docker-compose down -v
```

## More about the Data

**Three Cryptocurrencies:**
- **BTC-USD** - Bitcoin / US Dollar Tether
- **ETH-USD** - Ethereum / US Dollar Tether  
- **USDT-USD** - Tether / US Dollar Tether

**Trade Data Fields:**
- `symbol` - Trading pair
- `price` - Trade price (float)
- `quantity` - Trade quantity (float)
- `timestamp` - Trade timestamp in milliseconds
- `trade_id` - Unique trade identifier
- `is_buyer_maker` - Whether buyer is maker (boolean)

## Knobs for evaluating the system performace metrics
All configuration is in `.env` file:

```bash
# Change which cryptocurrencies to stream
SYMBOLS=BTCUSDT,ETHUSDT,USDTUSDT

# Kafka partitions (for throughput testing later)
KAFKA_PARTITIONS=4

# Batch size (for latency vs throughput testing later)
BATCH_SIZE=1

# Replay speed (for stress testing later)
REPLAY_SPEED=1

# Max poll records (for memory/throughput tuning later)
MAX_POLL_RECORDS=500
```

**These knobs enable testing of:**
- **Latency:** Compare batch=1 vs batch=32
- **Throughput:** Test 1 vs 4 Kafka partitions
- **Resource Usage:** Vary symbols count and replay speed

## How to process the data?
```bash
export KAFKA_BOOTSTRAP="localhost:29092"
export KAFKA_TOPIC="crypto-trades"
export OUTPUT_DIR="$(pwd)/data/outputs"
python src/consumer/stream_processor.py
```
The parquet should look like:

timestamp       open       high        low      close  \
0 2025-11-10 02:18:08+00:00  105828.33  105828.33  105828.33  105828.33   
1 2025-11-10 02:18:09+00:00  105828.33  105828.33  105797.67  105799.75   
2 2025-11-10 02:18:09+00:00  105792.68  105793.49  105792.68  105793.49   
3 2025-11-10 02:18:10+00:00  105791.54  105791.54  105785.42  105785.42   
4 2025-11-10 02:18:11+00:00  105785.41  105785.41  105785.41  105785.41   

   symbol    volume        date  
0  BTCUSD  0.000091  2025-11-10  
1  BTCUSD  0.239019  2025-11-10  
2  BTCUSD  0.002083  2025-11-10  
3  BTCUSD  0.000058  2025-11-10  
4  BTCUSD  0.000011  2025-11-10

The high means the highest price during the 1 second. The low means the lowest price in the 1 sec. The open means the Opening price. 

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f producer
docker-compose logs -f consumer
docker-compose logs -f kafka

# Restart a service
docker-compose restart producer
docker-compose restart consumer
docker-compose restart kafka

# Check service status
docker-compose ps

# Clean everything (removes data)
docker-compose down -v


# Verify Kafka topic exists:
docker exec kafka kafka-topics --describe --topic crypto-trades --bootstrap-server localhost:9092

# Check consumer group:
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group crypto-consumer-group

# Verify Kafka is accessible
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

