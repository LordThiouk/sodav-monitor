#!/bin/bash
set -e

echo "🚀 Starting local E2E test workflow"

# Create directories for test results and coverage reports
echo "📁 Creating directories for test results and coverage reports"
mkdir -p test-results coverage-reports

# Install dependencies
echo "📦 Installing dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pre-commit

# Run pre-commit hooks
echo "🔍 Running pre-commit hooks"
pre-commit install
pre-commit run --all-files || echo "Pre-commit hooks completed with warnings"

# Run E2E tests
echo "🧪 Running E2E tests"
python -m pytest tests/e2e/ -v

echo "✅ E2E tests completed"
