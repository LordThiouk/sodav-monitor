#!/bin/bash
set -e

echo "🚀 Running GitHub Actions workflow locally using act"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ act is not installed. Please install it first:"
    echo "  brew install act"
    exit 1
fi

# Create directories for test results and coverage reports
echo "📁 Creating directories for test results and coverage reports"
mkdir -p test-results coverage-reports

# Ask which workflow to run
echo "📋 Select a workflow to run:"
echo "  1) E2E Tests with Pydantic compatibility (e2e_tests_pydantic_compat.yml)"
echo "  2) Run E2E Tests on Push (run_on_push.yml)"
echo "  3) E2E Tests Local (e2e_tests_local.yml)"
echo "  4) E2E Tests with Docker (e2e_tests_docker.yml)"
read -p "Enter your choice (1-4): " workflow_choice

case $workflow_choice in
    1)
        echo "🧪 Running E2E tests with Pydantic compatibility"
        act -j e2e-tests -W .github/workflows/e2e_tests_pydantic_compat.yml --bind
        ;;
    2)
        echo "🧪 Running E2E tests on Push workflow"
        act -j e2e-tests -W .github/workflows/run_on_push.yml --bind
        ;;
    3)
        echo "🧪 Running E2E tests Local workflow"
        act -j e2e-tests -W .github/workflows/e2e_tests_local.yml --bind
        ;;
    4)
        echo "🧪 Running E2E tests with Docker workflow"
        act -j e2e-tests -W .github/workflows/e2e_tests_docker.yml --bind
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo "✅ GitHub Actions workflow completed"
