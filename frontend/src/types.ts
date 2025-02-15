export interface TrackAnalytics {
  id: number;
  title: string;
  artist: string;
  album?: string;
  isrc?: string;
  label?: string;
  detection_count: number;
  total_play_time: number; // Changed to number
  unique_stations: number;
  stations: string[];
}

export interface RadioStation {
  id: number;
  name: string;
  stream_url: string;
  country: string;
  language: string;
  is_active: number;
  last_checked: string;
  total_play_time: string;
  codec?: string;
  bitrate?: number;
  favicon?: string;
  homepage?: string;
  tags?: string[];
  last_detection?: {
    title: string;
    artist: string;
    confidence: number;
    detected_at: string;
    total_tracks: number;
  };
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
  external_ids?: Record<string, string>;
  created_at: string;
}

export interface TrackDetection {
  id: number;
  station_id: number;
  track_id: number;
  station_name: string;
  track_title: string;
  artist: string;
  detected_at: string;
  confidence: number;
  play_duration: number;
  track?: Track;
}

export interface ExternalRadioStation {
  stationuuid: string;
  name: string;
  url: string;
  url_resolved: string;
  country: string;
  language: string;
  lastcheckok: number;
  lastchecktime: string;
  favicon?: string;
  tags?: string;
  codec?: string;
  bitrate?: number;
  homepage?: string;
}

export interface RadioBrowserError {
  code: string;
  message: string;
}

export class RadioBrowserException extends Error {
  constructor(public error: RadioBrowserError) {
    super(error.message);
    this.name = 'RadioBrowserException';
  }
}

export interface Report {
  id: number;
  type: string;
  status: string;
  format: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface TrackAnalytics {
  id: number;
  title: string;
  artist: string;
  album?: string;
  isrc?: string;
  label?: string;
  detection_count: number;
  total_play_time: number;
  unique_stations: number;
  stations: string[];
}
