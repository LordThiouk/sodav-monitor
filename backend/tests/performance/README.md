# Performance Testing Framework for SODAV Monitor

This directory contains performance tests for the SODAV Monitor system, specifically focused on determining how many radio stations can be monitored simultaneously.

## Overview

The performance tests measure:

1. **Processing Time**: How long it takes to process a certain number of stations
2. **Throughput**: How many stations can be processed per second
3. **Resource Usage**: CPU and memory usage during station monitoring
4. **Concurrency Impact**: How different concurrency levels affect performance

Based on these measurements, the tests estimate the optimal number of stations that can be monitored simultaneously.

## Test Files

- `test_station_monitoring.py`: Contains tests for station monitoring performance, concurrent processing, and resource usage

## Running the Tests

You can run the tests using pytest:

```bash
# Run all performance tests
python -m pytest -xvs backend/tests/performance/

# Run specific tests
python -m pytest -xvs backend/tests/performance/test_station_monitoring.py::test_create_stations
python -m pytest -xvs backend/tests/performance/test_station_monitoring.py::test_concurrent_processing_simulation
python -m pytest -xvs backend/tests/performance/test_station_monitoring.py::test_resource_usage_simulation
```

## Generating Reports

There are two ways to generate performance reports:

### 1. Using the Test Runner Script

```bash
python backend/scripts/performance/run_station_monitoring_tests.py
```

This script will run the tests and generate a report with plots and visualizations.

### 2. Using the Report Generator Script

```bash
python backend/scripts/performance/generate_report.py
```

This script will generate a report based on predefined performance data.

## Report Location

Reports are saved in the `reports/performance/` directory with a timestamp.

## Interpreting Results

The performance tests provide several key metrics:

- **Average Processing Time**: The average time it takes to process a station
- **Average Stations Per Second**: The average number of stations that can be processed per second
- **Estimated Optimal Stations**: The estimated number of stations that can be processed within a 60-second window
- **Optimal Concurrency Level**: The concurrency level that provides the best throughput
- **Maximum Stations**: The estimated maximum number of stations that can be monitored based on system resources

## Current Results

Based on our simulated tests, the SODAV Monitor system can effectively monitor:

- **Optimal Number of Stations**: 240 stations (based on a 60-second processing window)
- **Optimal Concurrency Level**: 20 (provides the best throughput)
- **Maximum Stations Based on Resources**: 200 (limited by CPU and memory usage)

## Recommendations

1. For optimal performance, monitor no more than 200-240 stations simultaneously
2. Use a concurrency level of 20 for best throughput
3. Monitor system resources (CPU, memory) during operation to ensure they stay within acceptable limits

## Future Improvements

1. Implement real-world performance tests with actual radio stations
2. Add more detailed resource monitoring
3. Test with different hardware configurations
4. Implement load testing to determine system stability under heavy load 