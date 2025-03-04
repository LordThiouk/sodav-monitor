#!/usr/bin/env python
"""
Script to run all the migration steps in one go.
This script will:
1. Run the SQL script to add the updated_at column to the users table
2. Update the Alembic revision to include the migration
3. Run the tests to verify the updated_at column functionality
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the output."""
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode

def main():
    """Run all migration steps."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.absolute()
    
    # Step 1: Run the SQL script
    print("\n=== Step 1: Running SQL script to add updated_at column ===")
    sql_script_path = os.path.join(project_root, "backend", "migrations", "sql", "add_updated_at_to_users.sql")
    sql_command = f"psql -U sodav -d sodav_dev -f {sql_script_path}"
    if run_command(sql_command, cwd=project_root) != 0:
        print("Failed to run SQL script")
        return 1
    
    # Step 2: Update Alembic revision
    print("\n=== Step 2: Updating Alembic revision ===")
    update_script_path = os.path.join(project_root, "backend", "scripts", "migrations", "update_alembic_revision.py")
    if run_command(f"python {update_script_path}", cwd=project_root) != 0:
        print("Failed to update Alembic revision")
        return 1
    
    # Step 3: Run tests
    print("\n=== Step 3: Running tests ===")
    test_script_path = os.path.join(project_root, "backend", "scripts", "migrations", "run_updated_at_tests.py")
    if run_command(f"python {test_script_path}", cwd=project_root) != 0:
        print("Tests failed")
        return 1
    
    print("\n=== All migration steps completed successfully ===")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 