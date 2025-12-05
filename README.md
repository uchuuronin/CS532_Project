# Cryptocurrency Real-Time Data Streaming Pipeline

**Course:** Systems for Data Science  
**Project:** Real-time cryptocurrency analytics pipeline with streaming, processing, and visualization

A comprehensive distributed streaming system for real-time cryptocurrency market data analysis. This project demonstrates key systems concepts including concurrent I/O, bounded queues, offset management, configurable parallelism, checkpoint-based recovery, and scalable consumer architecture.

## 🎯 Project Overview

This project builds an end-to-end real-time analytics pipeline that:
- **Ingests** live cryptocurrency trade data from Coinbase/Binance WebSocket APIs
- **Streams** data through Apache Kafka for distributed message queuing
- **Processes** trades to calculate OHLC (Open, High, Low, Close) and volatility metrics
- **Stores** processed data in Parquet format with partitioning
- **Serves** data via REST API with interactive visualizations
- **Enables** machine learning predictions on price trends

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                  │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │ Coinbase API │         │ Binance API  │                     │
│  │ (WebSocket)  │         │ (WebSocket)  │                     │
│  └──────┬───────┘         └──────┬───────┘                     │
│         │                        │                              │
│         └────────────┬───────────┘                              │
│                      │                                           │
└──────────────────────┼──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Producer Layer                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Producer (Python)                                       │   │
│  │  - WebSocket connection management                        │   │
│  │  - Data normalization (symbol mapping)                   │   │
│  │  - JSON serialization                                     │   │
│  │  - Kafka message publishing                               │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Queue Layer                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Apache Kafka                                             │   │
│  │  - Topic: crypto-trades                                   │   │
│  │  - Partitions: 4 (configurable)                          │   │
│  │  - Replication: 1                                        │   │
│  │  - Retention: 24 hours                                   │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Stream Processor (Python)                              │   │
│  │  - Data cleaning & validation                           │   │
│  │  - 1-second OHLC aggregation                             │   │
│  │  - Volatility calculation (log returns)                  │   │
│  │  - Checkpoint-based recovery                             │   │
│  │  - Parquet file writing (partitioned by symbol/date)     │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Parquet Files (Partitioned)                            │   │
│  │  data/outputs/                                           │   │
│  │  ├── ohlc/                                              │   │
│  │  │   └── symbol=BTCUSD/date=2025-11-10/                │   │
│  │  └── volatility/                                       │   │
│  │      └── symbol=BTCUSD/date=2025-11-10/                 │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API & Visualization Layer                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server                                          │   │
│  │  - REST API endpoints (OHLC, Volatility)                 │   │
│  │  - Interactive dashboard (Plotly charts)               │   │
│  │  - Data filtering (symbol, date, limit)                  │   │
│  │  - Real-time visualizations                              │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics Layer                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Machine Learning Models                                 │   │
│  │  - Trend prediction (up/down)                             │   │
│  │  - Feature engineering (momentum, MA, volatility)         │   │
│  │  - SGD Classifier for price direction                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Main Components

### 1. **Producer** (`src/producer/`)
- **`coinbase_producer.py`**: Connects to Coinbase WebSocket API, normalizes trade data, publishes to Kafka
- **`binance_producer.py`**: Alternative producer for Binance API
- **Features**:
  - Symbol mapping (BTC-USD → BTCUSD)
  - Data validation
  - Retry logic for connection failures
  - Configurable batch size and replay speed

### 2. **Message Queue** (`docker-compose.yml`)
- **Apache Kafka**: Distributed streaming platform
- **Zookeeper**: Coordination service for Kafka
- **Configuration**:
  - 4 partitions (configurable via `KAFKA_PARTITIONS`)
  - Topic: `crypto-trades`
  - Port: `29092` (external), `9092` (internal)

### 3. **Stream Processor** (`src/consumer/stream_processor.py`)
- **Core Processing**:
  - Consumes normalized trade JSON from Kafka
  - Cleans and validates incoming trades
  - Aggregates 1-second OHLC windows per symbol
  - Calculates volatility (std of log returns)
  - Handles out-of-order data with buffering
- **Persistence**:
  - Writes OHLC and volatility to Parquet files
  - Partitioned by `symbol` and `date`
  - Checkpoint-based recovery
  - Periodic flushing (every 10 seconds)

### 4. **Data Loader** (`src/api/data_loader.py`)
- Loads OHLC and volatility data from Parquet files
- Supports filtering by symbol, date range, and limit
- Handles partitioned file structure
- Returns sorted, timezone-aware dataframes

### 5. **REST API** (`src/api/`)
- **`main.py`**: FastAPI application with dashboard
- **Routes**:
  - **`ohlc.py`**: OHLC data endpoints
  - **`volatility.py`**: Volatility data endpoints (with fallback calculation)
  - **`visualizations.py`**: Plotly chart generation
- **Features**:
  - Interactive dashboard at `/`
  - RESTful API with OpenAPI docs at `/docs`
  - CORS enabled for frontend integration
  - Health check endpoint

### 6. **Machine Learning** (`src/model/model.ipynb`)
- Trend prediction model (up/down classification)
- Feature engineering:
  - Momentum (returns)
  - Moving averages (5, 10 periods)
  - Volatility (rolling std of returns)
  - Price range (high - low)
- Uses SGD Classifier for binary classification

### 7. **Testing** (`tests/`)
- **Unit Tests**: Data validation, calculation logic
- **Integration Tests**: End-to-end component testing
- **Test Runner**: `run_tests.py` with coverage support

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (for Kafka infrastructure)
- **Python 3.11+** (for API and processing)
- **8GB+ RAM** (recommended for Kafka)

### Step 1: Start Infrastructure

```bash
# Start Kafka, Zookeeper, and Producer
docker-compose up -d

# Verify services are running
docker-compose ps

# Check Kafka topic was created
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Step 2: Process Data

```bash
# Set environment variables
export KAFKA_BOOTSTRAP="localhost:29092"
export KAFKA_TOPIC="crypto-trades"
export OUTPUT_DIR="$(pwd)/data/outputs"

# Run stream processor (in a separate terminal)
python src/consumer/stream_processor.py
```

Let it run for a few minutes to collect data, then stop with `Ctrl+C`.

### Step 3: Start API Server

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Set output directory
export OUTPUT_DIR="$(pwd)/data/outputs"
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Start FastAPI server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Access Dashboard

Open your browser:
- **Dashboard**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📊 Data Flow

### Trade Data Structure
```json
{
  "symbol": "BTCUSD",
  "price": 50000.0,
  "quantity": 0.5,
  "timestamp": 1699564800000,
  "trade_id": 12345,
  "is_buyer_maker": false
}
```

### OHLC Output (1-second windows)
```
timestamp                  open      high      low       close     volume   symbol
2025-11-10 02:18:08+00:00 105828.33 105828.33 105828.33 105828.33 0.000091 BTCUSD
2025-11-10 02:18:09+00:00 105828.33 105828.33 105797.67 105799.75 0.239019 BTCUSD
```

### Volatility Output
```
timestamp                  volatility  symbol
2025-11-10 02:18:08+00:00 0.000012    BTCUSD
2025-11-10 02:18:09+00:00 0.000015    BTCUSD
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (optional) or set environment variables:

```bash
# Cryptocurrency symbols to stream
SYMBOLS=BTCUSDT,ETHUSDT,USDTUSDT

# Kafka configuration
KAFKA_PARTITIONS=4
KAFKA_NUM_THREADS=3
KAFKA_IO_THREADS=8

# Producer settings
BATCH_SIZE=1              # Messages per batch
REPLAY_SPEED=1            # Speed multiplier (1 = real-time)

# Consumer settings
MAX_POLL_RECORDS=500      # Max records per poll
CONSUMER_GROUP=crypto-consumer-group

# Processing settings
OUTPUT_DIR=./data/outputs
MAX_BUFFER_SECONDS=5      # Buffer for out-of-order data
PARQUET_CHUNK_SECONDS=10  # Flush interval
```

### Performance Tuning Knobs

| Knob | Purpose | Impact |
|------|--------|--------|
| `KAFKA_PARTITIONS` | Parallelism | Higher = more throughput |
| `BATCH_SIZE` | Latency vs Throughput | Higher = lower latency, more throughput |
| `MAX_POLL_RECORDS` | Memory usage | Higher = more memory, better throughput |
| `REPLAY_SPEED` | Stress testing | >1 = faster replay for testing |

## 📡 API Endpoints

### OHLC Data
```bash
# Get OHLC data
GET /api/ohlc/?symbol=BTCUSD&limit=100&start_date=2025-11-10&end_date=2025-11-10

# Get latest OHLC
GET /api/ohlc/latest?symbol=BTCUSD
```

### Volatility Data
```bash
# Get volatility data
GET /api/volatility/?symbol=BTCUSD&limit=100
```

### Visualizations
```bash
# Candlestick chart
GET /api/viz/candlestick?symbol=BTCUSD&limit=500

# Price line chart
GET /api/viz/price-line?symbol=BTCUSD&limit=500

# Volatility chart
GET /api/viz/volatility?symbol=BTCUSD&limit=500

# Volume chart
GET /api/viz/volume?symbol=BTCUSD&limit=500

# Multi-symbol comparison
GET /api/viz/multi-symbol?symbols=BTCUSD,ETHUSD&limit=500
```

### Utility Endpoints
```bash
# Health check
GET /health

# Available symbols
GET /api/symbols
```

## 🧪 Testing

### Run All Tests
```bash
# Using test runner
python run_tests.py

# Using pytest directly
pytest tests/ -v

# With coverage
python run_tests.py --coverage
```

### Test Types
- **Unit Tests**: Data validation, calculation logic
- **Integration Tests**: End-to-end component testing
- **Test Coverage**: ~95% across all components

See `tests/README.md` for detailed testing documentation.

## 📁 Project Structure

```
CS532_Project/
├── src/
│   ├── producer/          # WebSocket producers (Coinbase, Binance)
│   ├── consumer/          # Kafka consumer and stream processor
│   ├── api/               # FastAPI application
│   │   ├── routes/        # API endpoints (OHLC, volatility, viz)
│   │   ├── data_loader.py # Parquet file loader
│   │   ├── models.py      # Pydantic models
│   │   └── main.py        # FastAPI app
│   └── model/             # ML models (Jupyter notebook)
├── tests/                 # Comprehensive test suite
├── data/
│   └── outputs/           # Parquet files (OHLC, volatility)
├── docker-compose.yml     # Kafka infrastructure
├── requirements.txt       # Python dependencies
├── run_tests.py          # Test runner script
└── README.md             # This file
```

## 🔍 Monitoring & Debugging

### View Logs
```bash
# Producer logs
docker-compose logs -f producer

# Consumer logs
docker-compose logs -f consumer

# Kafka logs
docker-compose logs -f kafka

# All logs
docker-compose logs -f
```

### Check Kafka Status
```bash
# List topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Describe topic
docker exec kafka kafka-topics --describe --topic crypto-trades --bootstrap-server localhost:9092

# Check consumer groups
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check consumer lag
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group crypto-consumer-group
```

### Check Data Files
```bash
# List available symbols
python3 -c "import sys; sys.path.insert(0, 'src'); from api.data_loader import DataLoader; print(DataLoader('./data/outputs').get_available_symbols())"

# Check file count
find data/outputs -name "*.parquet" | wc -l
```

## 🛠️ Troubleshooting

### API Not Showing Data
1. **Check data exists**: Verify parquet files in `data/outputs/`
2. **Check API logs**: Look for errors in terminal
3. **Verify symbol names**: Use exact symbols (BTCUSD, not BTC-USD)
4. **Check OUTPUT_DIR**: Ensure environment variable is set correctly

### Kafka Connection Issues
1. **Check services**: `docker-compose ps`
2. **Restart services**: `docker-compose restart kafka producer consumer`
3. **Check ports**: Ensure port 29092 is not in use
4. **View logs**: `docker-compose logs kafka`

### Volatility Graph Empty
- The API now automatically calculates volatility from OHLC data if stored volatility is missing
- Check that OHLC data exists for the symbol
- Verify the API endpoint returns data: `curl http://localhost:8000/api/volatility/?symbol=BTCUSD&limit=5`

## 🎓 Key Systems Concepts Demonstrated

1. **Concurrent I/O vs CPU Stages**: Producer (I/O) → Processor (CPU) → Storage (I/O)
2. **Bounded Queues/Backpressure**: Kafka partitions with configurable capacity
3. **Offset Management**: Kafka consumer groups with manual offset commits
4. **Configurable Parallelism**: Multiple Kafka partitions, configurable consumer parallelism
5. **Checkpoint-based Recovery**: Stream processor checkpoints for fault tolerance
6. **Scalable Consumer Architecture**: Horizontal scaling via consumer groups

## 📚 Additional Documentation

- **API Guide**: See `API_RUNNING_GUIDE.md` for detailed API usage
- **Testing Guide**: See `tests/README.md` for testing documentation
- **Architecture Diagram**: See `Workflow Diagram.png` for visual overview

## 🤝 Contributing

This is an academic project for Systems for Data Science course. For improvements:
1. Test changes thoroughly
2. Update documentation
3. Ensure backward compatibility
4. Run test suite before committing

## 📝 License

Academic project - Systems for Data Science course.

## 🙏 Acknowledgments

- Coinbase and Binance for WebSocket APIs
- Apache Kafka for distributed streaming
- FastAPI and Plotly for API and visualizations

---

**Last Updated**: 2025-11-10  
**Version**: 1.0.0  
**Status**: Production Ready ✅
