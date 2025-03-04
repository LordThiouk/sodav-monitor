# Performance Testing for Station Monitoring

This document explains how to run performance tests to determine how many radio stations can be monitored simultaneously by the SODAV Monitor system.

## Overview

The performance tests measure:

1. **Processing Time**: How long it takes to process a certain number of stations
2. **Throughput**: How many stations can be processed per second
3. **Resource Usage**: CPU and memory usage during station monitoring
4. **Concurrency Impact**: How different concurrency levels affect performance

Based on these measurements, the tests estimate the optimal number of stations that can be monitored simultaneously.

## Prerequisites

Before running the performance tests, make sure you have the following installed:

- Python 3.8 or higher
- pytest
- matplotlib
- numpy
- psutil (optional, for resource usage tests)

You can install the required packages with:

```bash
pip install pytest matplotlib numpy psutil
```

## Running the Tests

### Option 1: Using the Test Runner Script

The easiest way to run the performance tests is to use the provided script:

```bash
python backend/scripts/performance/run_station_monitoring_tests.py
```

This script will:

1. Run all the performance tests
2. Parse the test output
3. Generate plots and visualizations
4. Create an HTML report with the results and recommendations

The report will be saved in the `reports/performance/` directory with a timestamp.

### Option 2: Running Tests Directly

You can also run the tests directly using pytest:

```bash
python -m pytest -xvs backend/tests/performance/test_station_monitoring.py
```

This will run the tests and output the results to the console, but won't generate plots or a report.

## Test Descriptions

The performance tests include:

### 1. Station Monitoring Performance Test

This test measures how long it takes to process different numbers of stations (5, 10, 20, 50, 100) and calculates the throughput (stations per second). It also estimates the optimal number of stations based on a target processing time of 60 seconds.

### 2. Concurrent Station Processing Test

This test measures how different concurrency levels (5, 10, 20, 50) affect the performance of processing 100 stations. It identifies the optimal concurrency level for maximum throughput.

### 3. System Resource Usage Test

This test measures CPU and memory usage during station monitoring with different numbers of stations (10, 50, 100). It estimates the maximum number of stations that can be monitored based on available system resources.

## Interpreting the Results

The test results provide several key metrics:

- **Average Processing Time**: The average time it takes to process a station
- **Average Stations Per Second**: The average number of stations that can be processed per second
- **Estimated Optimal Stations**: The estimated number of stations that can be processed within a 60-second window
- **Optimal Concurrency Level**: The concurrency level that provides the best throughput
- **Maximum Stations**: The estimated maximum number of stations that can be monitored based on system resources

These metrics can help you determine the optimal configuration for your SODAV Monitor deployment.

## Customizing the Tests

You can customize the tests by modifying the following parameters in `backend/tests/performance/test_station_monitoring.py`:

- `station_counts`: The number of stations to test (default: [5, 10, 20, 50, 100])
- `concurrency_levels`: The concurrency levels to test (default: [5, 10, 20, 50])
- `target_processing_time`: The target processing time for estimating optimal stations (default: 60 seconds)

## Troubleshooting

If you encounter issues running the tests:

1. Make sure all required packages are installed
2. Check that the database is properly configured and accessible
3. Ensure that the test user has sufficient permissions
4. Verify that the test stations are being created and cleaned up properly

If resource usage tests fail, make sure the `psutil` package is installed:

```bash
pip install psutil
```

## Conclusion

By running these performance tests, you can determine the optimal number of stations to monitor simultaneously based on your system's capabilities. This information can help you scale your SODAV Monitor deployment effectively. 