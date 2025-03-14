# SODAV Monitor Production-Like Test Environment

This README provides instructions on how to set up and use the production-like test environment for SODAV Monitor, which allows for comprehensive testing of all system components, including external detection services (AcoustID and AudD).

## Overview

The standard test environment has limitations, particularly with external detection services that require specific audio conversion libraries. This production-like environment closely mimics production, allowing for comprehensive testing of all system components.

## Setup Options

There are three ways to set up the production-like test environment:

1. **Manual Setup**: Follow the detailed instructions in [docs/tests/production_test_environment.md](docs/tests/production_test_environment.md)
2. **Automated Setup Script**: Use the provided setup scripts
3. **Docker Setup**: Use Docker Compose for a containerized environment

## Option 1: Manual Setup

For detailed step-by-step instructions, refer to [docs/tests/production_test_environment.md](docs/tests/production_test_environment.md).

## Option 2: Automated Setup Script

### Linux/macOS

```bash
# Make the script executable
chmod +x scripts/setup_production_test_env.sh

# Run the script
./scripts/setup_production_test_env.sh
```

### Windows

```powershell
# Run PowerShell as Administrator
# Navigate to the project directory
.\scripts\setup_production_test_env_windows.ps1
```

After running the setup script, follow the on-screen instructions to complete the setup.

## Option 3: Docker Setup

Using Docker is the easiest way to set up a consistent environment across different platforms.

### Prerequisites

- Docker and Docker Compose installed
- API keys for AcoustID and AudD

### Setup Steps

1. Set your API keys as environment variables:

```bash
# Linux/macOS
export ACOUSTID_API_KEY=your_acoustid_api_key
export AUDD_API_KEY=your_audd_api_key

# Windows (PowerShell)
$env:ACOUSTID_API_KEY="your_acoustid_api_key"
$env:AUDD_API_KEY="your_audd_api_key"
```

2. Build and run the Docker containers:

```bash
docker-compose -f docker-compose.test.yml up --build
```

This will:
- Set up PostgreSQL and Redis
- Install all required dependencies
- Run database migrations
- Generate test data
- Run the end-to-end tests

3. View the test results:

The test results will be available in the `test_results` directory, including an HTML report.

## Running Tests

After setting up the environment, you can run the tests as follows:

### Running All End-to-End Tests

```bash
python -m pytest backend/tests/integration/test_end_to_end.py -v
```

### Running a Specific Test

```bash
python -m pytest backend/tests/integration/test_end_to_end.py::TestEndToEnd::test_detection_workflow -v
```

### Running with Log Output

```bash
python -m pytest backend/tests/integration/test_end_to_end.py -v --log-cli-level=INFO
```

### Generating HTML Report

```bash
python -m pytest backend/tests/integration/test_end_to_end.py -v --html=test_results/e2e_test_report.html
```

## Verifying External Services

To verify that the external services are configured correctly:

```bash
python test_external_services.py
```

This script will test the connection to AcoustID and AudD and report any issues.

## Troubleshooting

### Common Issues

1. **Audio Conversion Failures**:
   - Ensure ffmpeg is properly installed: `ffmpeg -version`
   - Check that libsndfile is installed: `ldconfig -p | grep libsndfile`
   - Verify chromaprint installation: `fpcalc -version`

2. **API Key Issues**:
   - Verify API keys are correctly set in the .env file
   - Check API key validity by running the test_external_services.py script
   - Ensure you haven't exceeded API rate limits

3. **Database Connection Issues**:
   - Verify PostgreSQL is running
   - Check connection parameters in the .env file
   - Ensure the database user has proper permissions

4. **Redis Connection Issues**:
   - Verify Redis is running
   - Check Redis connection string in the .env file

5. **Python Package Issues**:
   - Ensure all dependencies are installed: `pip list`
   - Try reinstalling problematic packages: `pip uninstall package_name && pip install package_name`

### Getting Help

If you encounter issues not covered in this README, please:

1. Check the detailed documentation in [docs/tests/production_test_environment.md](docs/tests/production_test_environment.md)
2. Look for error messages in the logs
3. Consult the troubleshooting section in the documentation

## Conclusion

This production-like environment allows you to fully test all aspects of the SODAV Monitor system, including the external detection services that require specialized audio conversion capabilities. By using this environment, you can ensure that your tests accurately reflect how the system will behave in production.
