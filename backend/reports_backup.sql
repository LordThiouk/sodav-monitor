PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type VARCHAR NOT NULL CHECK (type IN ('daily', 'weekly', 'monthly', 'custom')),
    status VARCHAR DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'completed', 'failed')),
    format VARCHAR DEFAULT 'csv',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    filters JSON,
    file_path VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_reports_user ON reports(user_id);
CREATE INDEX idx_reports_status ON reports(status);
COMMIT;
