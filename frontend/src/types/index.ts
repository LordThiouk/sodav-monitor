// Radio Station Types
export interface ExternalRadioStation {
    changeuuid: string;
    stationuuid: string;
    name: string;
    url: string;
    url_resolved: string;
    homepage: string;
    favicon: string;
    tags: string;
    country: string;
    countrycode: string;
    language: string;
    votes: number;
    codec: string;
    bitrate: number;
    lastcheckok: boolean;
    lastchecktime: string;
    lastcheckoktime: string;
    clicktimestamp: string;
    clickcount: number;
    clicktrend: number;
}

export interface LastDetection {
    title: string;
    artist: string;
    confidence: number;
    total_tracks: number;
}

export interface RadioStation {
    id: number;
    name: string;
    stream_url: string;
    url_resolved: string;
    country: string;
    language: string;
    is_active: boolean;
    last_checked: string;
    // Extended properties
    favicon?: string;
    tags?: string[];
    codec?: string;
    bitrate?: number;
    homepage?: string;
    last_detection?: LastDetection;
}

// Error Types
export type RadioBrowserError =
    | 'NETWORK_ERROR'
    | 'INVALID_RESPONSE'
    | 'STATION_UNAVAILABLE';

export class RadioBrowserException extends Error {
    constructor(
        public type: RadioBrowserError,
        public details?: any
    ) {
        super(`RadioBrowser Error: ${type}`);
    }
}

export interface Track {
    id: number;
    title: string;
    artist: string;
    isrc?: string;
    label?: string;
    album?: string;
    release_date?: string;
    play_count: number;
    total_play_time: number;
    last_played?: string;
    external_ids?: Record<string, any>;
    created_at: string;
}

export interface TrackDetection {
    id: number;
    station_id: number;
    track_id: number;
    confidence: number;
    detected_at: string;
    play_duration: number;
    station?: RadioStation;
    track?: Track;
}

export interface Report {
    id: number;
    user_id: number;
    type: 'daily' | 'weekly' | 'monthly' | 'custom';
    status: 'pending' | 'generating' | 'completed' | 'failed';
    format: 'csv' | 'xlsx' | 'pdf';
    start_date: string;
    end_date: string;
    filters?: Record<string, any>;
    file_path?: string;
    created_at: string;
    completed_at?: string;
    error_message?: string;
}
