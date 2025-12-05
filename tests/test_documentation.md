# Documentation for Unit and Integration Tests

## Running Tests

### Using the Test Runner Script

The easiest way to run tests is using the `run_tests.py` script:

```bash
# Run all tests
python3 run_tests.py

# Run only unit tests
python3 run_tests.py --type unit

# Run only integration tests
python3 run_tests.py --type integration

# Run specific component tests
python3 run_tests.py --type producer
python3 run_tests.py --type stream_processor
python3 run_tests.py --type data_loader

# Run with coverage report
python3 run_tests.py --coverage

# List all available tests
python3 run_tests.py --list

# Check dependencies
python3 run_tests.py --check-deps
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_producer.py -v

# Run specific test class
pytest tests/test_producer.py::TestProducerDataValidation -v

# Run specific test method
pytest tests/test_producer.py::TestProducerDataValidation::test_trade_data_structure -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Using unittest

```bash
# Run all tests
python3 -m unittest discover tests

# Run specific test file
python3 -m unittest tests.test_producer

# Run specific test class
python3 -m unittest tests.test_producer.TestProducerDataValidation
```

## Troubleshooting

### Import Errors
If you get import errors, make sure:
- The `src` directory is in your Python path
- All dependencies are installed: `pip install -r requirements.txt`

### Test Failures
- Check that test data files exist (for integration tests)
- Verify environment variables are set correctly
- Check that temporary directories are writable

### Coverage Issues
- Make sure `pytest-cov` is installed
- Run with `--coverage` flag
- Check `htmlcov/index.html` for detailed coverage report

## Continuous Integration

These tests are designed to be run in CI/CD pipelines. Example GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python3 run_tests.py --coverage
```


## About the Tests:

### Unit Tests

1. **test_producer.py** - Tests producer data validation
   - Trade data structure validation
   - Price/quantity validation
   - Symbol mapping and normalization
   - JSON serialization
   - Error handling

2. **test_stream_processor.py** - Tests stream processing logic
   - Data cleaning and validation
   - OHLC calculation from trades
   - Volatility calculation
   - Data type consistency
   - Edge cases and error handling

3. **test_data_loader.py** - Tests API and data loader
   - Data filtering (symbol, date, limit)
   - API response formats
   - Data validation rules
   - Parquet path structure
   - Error handling

4. **test_endpoint.py** - Tests FastAPI endpoints
   - HTTP endpoint formats
   - Query parameter validation
   - Response structures
   - Error handling

### Integration Tests

1. **test_producer_integration.py** - Integration tests for producers
   - Actual Binance producer normalization
   - Actual Coinbase producer normalization
   - Real message format handling
   - Error handling with real data

2. **test_stream_processor_integration.py** - Integration tests for stream processor
   - Actual `clean_trade()` method testing
   - Real OHLC aggregation
   - Volume calculation
   - Volatility calculation logic
   - Utility function testing

3. **test_data_loader_integration.py** - Integration tests for data loader
   - Loading from actual parquet files
   - Symbol filtering
   - Date range filtering
   - Limit functionality
   - Error handling with real files
