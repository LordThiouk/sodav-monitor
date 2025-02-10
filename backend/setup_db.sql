-- Drop existing tables if they exist
DROP TABLE IF EXISTS track_detections;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS radio_stations;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS users;

-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    role VARCHAR DEFAULT 'user'
);

-- Create reports table
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type VARCHAR NOT NULL CHECK (type IN ('daily', 'weekly', 'monthly', 'custom')),
    status VARCHAR DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'completed', 'failed')),
    format VARCHAR DEFAULT 'csv',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    filters TEXT,
    file_path VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create radio_stations table
CREATE TABLE radio_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    stream_url VARCHAR NOT NULL,
    country VARCHAR,
    language VARCHAR,
    is_active INTEGER DEFAULT 1,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_detection_time TIMESTAMP,
    status VARCHAR DEFAULT 'active'
);

-- Create tracks table
CREATE TABLE tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR NOT NULL,
    artist VARCHAR NOT NULL,
    isrc VARCHAR,
    label VARCHAR,
    album VARCHAR,
    release_date VARCHAR,
    play_count INTEGER DEFAULT 0,
    total_play_time INTERVAL DEFAULT '0 seconds',
    last_played TIMESTAMP,
    external_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fingerprint VARCHAR,
    fingerprint_raw BLOB
);

-- Create track_detections table
CREATE TABLE track_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER,
    track_id INTEGER,
    confidence FLOAT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    play_duration INTERVAL,
    FOREIGN KEY (station_id) REFERENCES radio_stations(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

-- Analytics tables
CREATE TABLE IF NOT EXISTS analytics_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    detection_count INTEGER DEFAULT 0,
    detection_rate REAL DEFAULT 0.0,
    active_stations INTEGER DEFAULT 0,
    average_confidence REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS detection_hourly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour DATETIME,
    count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS artist_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_name TEXT NOT NULL,
    detection_count INTEGER DEFAULT 0,
    last_detected DATETIME,
    UNIQUE(artist_name)
);

CREATE TABLE IF NOT EXISTS track_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    detection_count INTEGER DEFAULT 0,
    last_detected DATETIME,
    average_confidence REAL DEFAULT 0.0,
    FOREIGN KEY (track_id) REFERENCES tracks(id),
    UNIQUE(track_id)
);

-- Create indices for better performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_reports_user ON reports(user_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_tracks_isrc ON tracks(isrc);
CREATE INDEX idx_tracks_label ON tracks(label);
CREATE INDEX idx_detections_station ON track_detections(station_id);
CREATE INDEX idx_detections_track ON track_detections(track_id);
CREATE INDEX idx_detections_time ON track_detections(detected_at);

-- Create indexes for analytics tables
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_detection_hourly_hour ON detection_hourly(hour);
CREATE INDEX IF NOT EXISTS idx_artist_stats_count ON artist_stats(detection_count);
CREATE INDEX IF NOT EXISTS idx_track_stats_count ON track_stats(detection_count);
