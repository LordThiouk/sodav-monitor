-- Create station_track_stats table
CREATE TABLE station_track_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER,
    track_id INTEGER,
    play_count INTEGER DEFAULT 0,
    total_play_time INTERVAL DEFAULT '0 seconds',
    first_played TIMESTAMP,
    last_played TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES radio_stations(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
