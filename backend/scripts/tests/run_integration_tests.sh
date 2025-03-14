#!/bin/bash

# Script to run integration tests and generate coverage report
# Usage: ./scripts/run_integration_tests.sh

# Set the working directory to the project root
cd "$(dirname "$0")/.."

# Set environment variables for testing
export PYTHONPATH=.
export TEST_DATABASE_URL=sqlite:///./test.db
export TEST_REDIS_URL=redis://localhost:6379/1
export TEST_API_KEY=test_key
export ACOUSTID_API_KEY=test_acoustid_key
export AUDD_API_KEY=test_audd_key

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-benchmark

# Run the integration tests with coverage
echo "Running integration tests with coverage..."
python -m pytest backend/tests/integration/ -v --cov=backend --cov-report=html:coverage_integration --cov-report=term

# Generate a summary report
echo "Generating summary report..."
echo "Integration Test Coverage Report" > integration_test_report.txt
echo "=============================" >> integration_test_report.txt
echo "" >> integration_test_report.txt
echo "Date: $(date)" >> integration_test_report.txt
echo "" >> integration_test_report.txt
echo "Coverage Summary:" >> integration_test_report.txt
python -m pytest backend/tests/integration/ --cov=backend --cov-report=term-missing | grep -A 100 "TOTAL" | head -n 20 >> integration_test_report.txt
echo "" >> integration_test_report.txt
echo "Test Results:" >> integration_test_report.txt
python -m pytest backend/tests/integration/ -v | grep -E "PASSED|FAILED|ERROR|SKIPPED" >> integration_test_report.txt

echo "Integration tests completed. See coverage_integration/ for detailed coverage report."
echo "Summary report saved to integration_test_report.txt"
