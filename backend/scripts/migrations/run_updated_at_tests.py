#!/usr/bin/env python
"""
Script to run tests for the updated_at column functionality.
This script runs the tests in backend/tests/models/test_updated_at.py
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, cwd=None, env=None):
    """Run a command and return the output."""
    print(f"Running command: {command}")

    # Use current environment if none provided
    if env is None:
        env = os.environ.copy()

    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, env=env)
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode


if __name__ == "__main__":
    print("Running updated_at column tests...")

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent.absolute()
    print(f"Project root: {project_root}")

    # Change to the project root directory
    os.chdir(project_root)

    # Clean up test data to avoid unique constraint violations
    print("Cleaning up test data...")
    cleanup_cmd = """
    psql -U sodav -d sodav_dev -c "
    DELETE FROM users WHERE email LIKE 'test_user%' OR username LIKE 'test_user%';
    DELETE FROM artists WHERE name LIKE 'Test Artist%' OR name LIKE 'Updated Test%';
    "
    """
    cleanup_result = run_command(cleanup_cmd)
    if cleanup_result != 0:
        print("Warning: Test data cleanup may not have completed successfully.")

    # Set up environment with PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Run the tests with absolute path
    print("Starting tests...")
    test_file = project_root / "backend" / "tests" / "models" / "test_updated_at.py"
    test_cmd = f"python -m pytest -xvs {test_file}"
    test_result = run_command(test_cmd, env=env)

    if test_result == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)
