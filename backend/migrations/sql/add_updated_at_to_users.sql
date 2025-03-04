-- Add updated_at column to users table
ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT NOW(); 