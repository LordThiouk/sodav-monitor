-- Drop existing tables if they exist
DROP TABLE IF EXISTS track_detections;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS radio_stations;

-- Create radio_stations table
CREATE TABLE radio_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    stream_url VARCHAR NOT NULL,
    country VARCHAR,
    language VARCHAR,
    is_active INTEGER DEFAULT 1,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create tracks table with ISRC and label
CREATE TABLE tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR NOT NULL,
    artist VARCHAR NOT NULL,
    isrc VARCHAR,  -- International Standard Recording Code
    label VARCHAR, -- Record label
    album VARCHAR, -- Album name
    release_date VARCHAR,
    play_count INTEGER DEFAULT 0,
    total_play_time INTEGER DEFAULT 0,  -- Stored in seconds
    last_played TIMESTAMP,
    external_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create track_detections table
CREATE TABLE track_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER,
    track_id INTEGER,
    confidence FLOAT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    play_duration INTEGER,  -- Duration in seconds
    FOREIGN KEY (station_id) REFERENCES radio_stations(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

-- Create indices for better performance
CREATE INDEX idx_tracks_isrc ON tracks(isrc);
CREATE INDEX idx_tracks_label ON tracks(label);
CREATE INDEX idx_detections_station ON track_detections(station_id);
CREATE INDEX idx_detections_track ON track_detections(track_id);
CREATE INDEX idx_detections_time ON track_detections(detected_at);

-- Insert sample radio stations
INSERT INTO radio_stations (name, stream_url, country, language) VALUES
('UCAD FM', 'https://stream.zeno.fm/b38a68a1krquv', 'Senegal', 'French/Wolof'),
('Sud FM', 'https://stream.zeno.fm/d970hwkm1f8uv', 'Senegal', 'French/Wolof');

-- Insert sample tracks with ISRC and label
INSERT INTO tracks (title, artist, isrc, label, album, release_date) VALUES
('Yo male', 'Coumba Gawlo', 'QMDA71835492', 'Aldiana Records', 'Aldiana', '2008'),
('Boul Ko Fii', 'Youssou NDour', 'QMDA72046183', 'Prince Arts', 'Set', '2010');
