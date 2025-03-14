# Running E2E Tests Locally

This document explains how to run the End-to-End (E2E) tests for the SODAV Monitor system locally without Docker.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database running locally
- Environment variables set up correctly (via `.env` file)

## Setup

1. Make sure your PostgreSQL database is running and accessible with the credentials specified in your `.env` file.

2. Install the required dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-asyncio pre-commit
   ```

3. Create directories for test results and coverage reports:
   ```bash
   mkdir -p test-results coverage-reports
   ```

## Running the Tests

You can run the E2E tests using the provided script:

```bash
./run_e2e_tests_local.sh
```

Or run them directly with pytest:

```bash
python -m pytest tests/e2e/ -v
```

## Test Results

After running the tests, you can find:
- Coverage reports in the `coverage-reports/` directory
- Test results in the `test-results/` directory

## GitHub Workflow

The E2E tests are also configured to run in GitHub Actions using the workflow defined in `.github/workflows/e2e_tests_local.yml`. This workflow:

1. Sets up a PostgreSQL database
2. Installs dependencies
3. Runs pre-commit hooks
4. Executes the E2E tests
5. Uploads test results as artifacts

You can manually trigger this workflow from the GitHub Actions tab.

## Notes

- The `test_api_endpoints` test will be skipped if the backend server is not running. To run this test, start the backend server on port 8000 before running the tests.
- Some tests may require additional setup, such as Redis or other external services. Refer to the test documentation for specific requirements.
