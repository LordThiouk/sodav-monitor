# Updated_at Column Migration

This repository contains scripts and files for adding the `updated_at` column to the database tables in the SODAV Monitor project.

## Files

- `backend/migrations/sql/add_updated_at_to_users.sql`: SQL script to add the `updated_at` column to the `users` table.
- `backend/migrations/versions/2024_03_updated_at.py`: Alembic migration file to document the changes.
- `backend/scripts/migrations/update_alembic_revision.py`: Script to update the Alembic revision to include the migration.
- `backend/scripts/migrations/run_updated_at_tests.py`: Script to run tests for the `updated_at` column functionality.
- `backend/scripts/migrations/run_migration.py`: Script to run all the migration steps in one go.
- `docs/updated_at_migration.md`: Documentation explaining the migration process.

## Running the Migration

To run the migration, execute the following command:

```bash
python backend/scripts/migrations/run_migration.py
```

This will:
1. Run the SQL script to add the `updated_at` column to the `users` table.
2. Update the Alembic revision to include the migration.
3. Run the tests to verify the `updated_at` column functionality.

## Verifying the Migration

To verify that the migration was successful, run the following command:

```bash
python backend/scripts/migrations/check_migration.py
```

This will check if the `updated_at` column exists in the database tables and if it is being updated correctly.

## Manual Steps

If you prefer to run the migration steps manually, follow these steps:

1. Run the SQL script to add the `updated_at` column to the `users` table:
   ```bash
   psql -U sodav -d sodav_dev -f backend/migrations/sql/add_updated_at_to_users.sql
   ```

2. Update the Alembic revision to include the migration:
   ```bash
   python backend/scripts/migrations/update_alembic_revision.py
   ```

3. Run the tests to verify the `updated_at` column functionality:
   ```bash
   python backend/scripts/migrations/run_updated_at_tests.py
   ```

## Documentation

For more detailed information about the migration process, see the [documentation](updated_at_migration.md). 