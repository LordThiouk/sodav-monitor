#!/bin/bash

# Script to run all tests (unit and integration) and generate a combined coverage report
# Usage: ./scripts/run_all_tests.sh

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

# Run all tests with coverage
echo "Running all tests with coverage..."
python -m pytest backend/tests/ -v --cov=backend --cov-report=html:coverage_all --cov-report=term

# Generate a summary report
echo "Generating summary report..."
echo "Complete Test Coverage Report" > all_tests_report.txt
echo "===========================" >> all_tests_report.txt
echo "" >> all_tests_report.txt
echo "Date: $(date)" >> all_tests_report.txt
echo "" >> all_tests_report.txt
echo "Coverage Summary:" >> all_tests_report.txt
python -m pytest backend/tests/ --cov=backend --cov-report=term-missing | grep -A 100 "TOTAL" | head -n 20 >> all_tests_report.txt
echo "" >> all_tests_report.txt
echo "Test Results:" >> all_tests_report.txt
python -m pytest backend/tests/ -v | grep -E "PASSED|FAILED|ERROR|SKIPPED" >> all_tests_report.txt

echo "All tests completed. See coverage_all/ for detailed coverage report."
echo "Summary report saved to all_tests_report.txt"
