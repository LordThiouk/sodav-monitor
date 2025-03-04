# Updated_at Column Migration

This document explains the migration process for adding the `updated_at` column to the database tables.

## Overview

The `updated_at` column is used to track when a record was last updated. This is useful for auditing and tracking changes to the database.

## Migration Process

The migration process involved the following steps:

1. Created a SQL script (`backend/migrations/sql/add_updated_at_to_users.sql`) to add the `updated_at` column to the `users` table.
2. Executed the SQL script to add the column to the database.
3. Created an Alembic migration file (`backend/migrations/versions/2024_03_updated_at.py`) to document the changes.
4. Updated the Alembic revision to include the migration.
5. Added event listeners to automatically update the `updated_at` column when a record is modified.

## Files Created

- `backend/migrations/sql/add_updated_at_to_users.sql`: SQL script to add the `updated_at` column to the `users` table.
- `backend/migrations/versions/2024_03_updated_at.py`: Alembic migration file to document the changes.
- `backend/scripts/migrations/update_alembic_revision.py`: Script to update the Alembic revision to include the migration.
- `backend/scripts/migrations/run_updated_at_tests.py`: Script to run tests for the `updated_at` column functionality.
- `backend/scripts/migrations/check_migration.py`: Script to check if the migration was successful.
- `backend/scripts/migrations/check_alembic_version.py`: Script to check the Alembic version table.
- `backend/scripts/migrations/run_migration.py`: Script to run all migration steps in one go.

## Event Listeners

The `updated_at` column is automatically updated when a record is modified using SQLAlchemy event listeners. The event listeners are defined in `backend/models/database.py`:

```python
@event.listens_for(SessionLocal, 'before_flush')
def before_flush(session, flush_context, instances):
    for instance in session.dirty:
        # Check if the instance has an updated_at attribute
        if hasattr(instance, 'updated_at'):
            # Update the updated_at attribute
            instance.updated_at = datetime.utcnow()
```

## Testing

The `updated_at` column functionality is tested in `backend/tests/models/test_updated_at.py`. The tests verify that the `updated_at` column is automatically updated when a record is modified.

## Verification

To verify that the migration was successful, run the following command:

```bash
python backend/scripts/migrations/check_migration.py
```

This will check if the `updated_at` column exists in the database tables and if it is being updated correctly. 