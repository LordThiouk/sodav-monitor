# Running Tests in Docker Development Environment

This guide explains how to run the SODAV Monitor end-to-end tests in your existing Docker development environment.

## Prerequisites

1. Docker Desktop installed and running
2. PowerShell (for Windows) or Bash (for Linux/macOS)

## Available Test Scripts

We've created several PowerShell scripts to make it easy to run different tests:

1. `scripts/docker_tests/run_tests_in_docker.ps1` - Runs all end-to-end tests
2. `scripts/docker_tests/run_detection_test_in_docker.ps1` - Runs only the detection workflow test
3. `scripts/docker_tests/run_report_test_in_docker.ps1` - Runs only the report generation test
4. `scripts/docker_tests/run_play_duration_test_in_docker.ps1` - Runs only the play duration accuracy test
5. `scripts/docker_tests/run_end_to_end_workflow_test_in_docker.ps1` - Runs only the end-to-end workflow test

## Running the Tests

### Step 1: Start Docker Desktop

Make sure Docker Desktop is running on your system before executing any of the test scripts.

### Step 2: Run the Test Scripts

To run all end-to-end tests:

```powershell
.\scripts\docker_tests\run_tests_in_docker.ps1
```

To run a specific test:

```powershell
# For detection workflow test
.\scripts\docker_tests\run_detection_test_in_docker.ps1

# For report generation test
.\scripts\docker_tests\run_report_test_in_docker.ps1

# For play duration accuracy test
.\scripts\docker_tests\run_play_duration_test_in_docker.ps1

# For end-to-end workflow test
.\scripts\docker_tests\run_end_to_end_workflow_test_in_docker.ps1
```

## What the Scripts Do

Each script performs the following steps:

1. Checks if Docker is running
2. Checks if the SODAV containers are already running
   - If not, it starts them using the `start-docker.ps1` script
   - Waits for the containers to be ready
3. Executes the specified test(s) in the backend container
4. Displays the test results

## Viewing Test Results

The test results will be displayed in the console. You can also check the logs in the `logs` directory for more detailed information.

## Troubleshooting

### Docker Not Running

If you see an error message saying "Docker is not running", make sure Docker Desktop is started and running properly.

### Containers Not Starting

If the containers fail to start, check the Docker logs for more information:

```powershell
docker logs sodav-backend
```

### Test Failures

If tests fail, the error messages will be displayed in the console. You can also check the logs for more detailed information:

```powershell
# View backend logs
docker logs sodav-backend
```

## Notes on External Services

In the development environment, external detection services (AcoustID and AudD) may not function exactly as they would in production:

- AcoustID and AudD detection may fail with "Failed to convert features to audio" errors
- These errors are expected in the development environment and the tests are designed to handle them gracefully
- No match being found is considered a valid test outcome
- These limitations are logged but don't cause test failures

For complete testing of external detection services, a specialized production-like environment would be required. 