# Running the FastAPI API and Visualizations

This guide explains how to run the complete project with FastAPI integration and Plotly visualizations.

## Prerequisites

1. **Python 3.11+** installed
2. **Data files** - Either existing parquet files in `data/outputs/` OR run the stream processor first

## Step 1: Install Required Dependencies

```bash
pip install -r requirements.txt
```
This installs:
- FastAPI and Uvicorn (API server)
- Plotly (visualizations)
- Pandas, PyArrow (data processing)
- Kafka-python, websocket-client (streaming)

## Step 2: Ensure Data Exists
The API reads from parquet files in `data/outputs/`. You have two options:

### Option A: Use Existing Data
If you already have parquet files from previous runs, skip to Step 3.

### Option B: Generate New Data (Recommended for first run)

1. **Start Kafka and Producer** (using Docker):
   ```bash
   docker compose up -d
   ```

2. **Run the Stream Processor** (in a separate terminal):
   ```bash
   export KAFKA_BOOTSTRAP="localhost:29092"
   export KAFKA_TOPIC="crypto-trades"
   export OUTPUT_DIR="$(pwd)/data/outputs"
   python src/consumer/stream_processor.py
   ```
   
   Let it run for a few minutes to collect data, then stop it (Ctrl+C).

## Step 3: Start the FastAPI Server

```bash
export OUTPUT_DIR="$(pwd)/data/outputs"
# Start the FastAPI server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Or using Python directly:
```bash
export OUTPUT_DIR="$(pwd)/data/outputs"
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 4: Access the Application

Once the server is running, you'll see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Open Dashboard
Open in your browser:
```
http://localhost:8000/
```

Features:
- Select cryptocurrency symbol (BTCUSD, ETHUSD, USDTUSD)
- Choose chart type (Candlestick, Price Line, Volatility, Volume)
- Compare multiple symbols
- Adjust data limit

### API Documentation (Swagger UI)
```
http://localhost:8000/docs
```

### Alternative API Docs (ReDoc)
```
http://localhost:8000/redoc
```

## Available API Endpoints

### Data Endpoints

1. **Get OHLC Data**
   ```
   GET /api/ohlc/?symbol=BTCUSD&limit=100
   ```

2. **Get Latest OHLC**
   ```
   GET /api/ohlc/latest?symbol=BTCUSD
   ```

3. **Get Volatility Data**
   ```
   GET /api/volatility/?symbol=BTCUSD&limit=100
   ```

4. **Get Available Symbols**
   ```
   GET /api/symbols
   ```

5. **Health Check**
   ```
   GET /health
   ```

### Visualization Endpoints (Return Plotly JSON)

1. **Candlestick Chart**
   ```
   GET /api/viz/candlestick?symbol=BTCUSD&limit=500
   ```

2. **Price Line Chart**
   ```
   GET /api/viz/price-line?symbol=BTCUSD&limit=500
   ```

3. **Volatility Chart**
   ```
   GET /api/viz/volatility?symbol=BTCUSD&limit=500
   ```

4. **Volume Chart**
   ```
   GET /api/viz/volume?symbol=BTCUSD&limit=500
   ```

5. **Multi-Symbol Comparison**
   ```
   GET /api/viz/multi-symbol?symbols=BTCUSD,ETHUSD,USDTUSD&limit=500
   ```

## Example API Calls

### Using curl:

```bash
# Get OHLC data
curl "http://localhost:8000/api/ohlc/?symbol=BTCUSD&limit=10"

# Get latest OHLC
curl "http://localhost:8000/api/ohlc/latest?symbol=BTCUSD"

# Get available symbols
curl "http://localhost:8000/api/symbols"

# Get candlestick chart JSON
curl "http://localhost:8000/api/viz/candlestick?symbol=BTCUSD&limit=100"
```

### Using Python:

```python
import requests

# Get OHLC data
response = requests.get("http://localhost:8000/api/ohlc/", params={
    "symbol": "BTCUSD",
    "limit": 100
})
data = response.json()
print(f"Retrieved {data['count']} OHLC records")
```

## Troubleshooting

### Issue: "No data found for symbol"
- **Solution**: Make sure the stream processor has generated parquet files
- Check: `ls -la data/outputs/ohlc/symbol=BTCUSD/date=*/`

### Issue: Module not found errors
- **Solution**: Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the project root directory

### Issue: Port 8000 already in use
- **Solution**: Use a different port:
  ```bash
  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
  ```

### Issue: Empty charts or no data
- **Solution**: 
  1. Verify parquet files exist: `ls data/outputs/ohlc/`
  2. Check file permissions
  3. Ensure OUTPUT_DIR environment variable is set correctly

## Running Everything Together

For a complete setup, you can run all components:

**Terminal 1 - Kafka & Producer:**
```bash
docker compose up -d
```

**Terminal 2 - Stream Processor:**
```bash
export KAFKA_BOOTSTRAP="localhost:29092"
export KAFKA_TOPIC="crypto-trades"
export OUTPUT_DIR="$(pwd)/data/outputs"
python src/consumer/stream_processor.py
```

**Terminal 3 - FastAPI Server:**
```bash
export OUTPUT_DIR="$(pwd)/data/outputs"
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/ in your browser!

## Next Steps

- Explore the interactive dashboard
- Try different chart types
- Compare multiple cryptocurrencies
- Use the API endpoints in your own applications
- Check the API documentation at `/docs` for detailed endpoint information

