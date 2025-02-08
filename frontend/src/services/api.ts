import { RadioStation, Track, TrackDetection, Report } from '../types';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8002/api';

export interface Stream extends RadioStation {
  type: string;
  status: string;
  region: string;
  tracks_today: number;
  current_track: Track | null;
}

export interface StatsUpdateMessage {
  type: 'stats_update';
  timestamp: string;
  active_streams: number;
  total_streams: number;
  total_tracks: number;
}

export interface TrackDetectionMessage {
  type: 'track_detection';
  timestamp: string;
  stream_id: number;
  stream_name: string;
  detection: {
    title: string;
    artist: string;
    confidence: number;
    total_tracks: number;
  };
}

export type WebSocketMessage = StatsUpdateMessage | TrackDetectionMessage;

export const detectAudio = async (stationId: number): Promise<{
  detection: {
    title: string;
    artist: string;
    confidence: number;
    total_tracks: number;
  }
}> => {
  try {
    const response = await fetch(`${API_BASE_URL}/detect/${stationId}`, {
      method: 'POST'
    });
    if (!response.ok) {
      throw new Error('Failed to detect audio');
    }
    return await response.json();
  } catch (error) {
    console.error('Error detecting audio:', error);
    throw error;
  }
};

export const fetchStations = async (): Promise<RadioStation[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/stations`);
    if (!response.ok) {
      throw new Error('Failed to fetch stations');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching stations:', error);
    throw error;
  }
};

export const fetchDetections = async (stationId: number): Promise<TrackDetection[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/detections?station_id=${stationId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch detections');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching detections:', error);
    throw error;
  }
};

export const fetchTracks = async (): Promise<Track[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/tracks`);
    if (!response.ok) {
      throw new Error('Failed to fetch tracks');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching tracks:', error);
    throw error;
  }
};

export const fetchReports = async (): Promise<Report[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/reports`);
    if (!response.ok) {
      throw new Error('Failed to fetch reports');
    }
    const data = await response.json();
    return data.reports;
  } catch (error) {
    console.error('Error fetching reports:', error);
    return [];
  }
};

export interface WebSocketCleanup {
  cleanup: () => void;
  ws: WebSocket | null;
}

export const connectWebSocket = (onMessage: (data: WebSocketMessage) => void): WebSocketCleanup => {
  const ws = new WebSocket('ws://localhost:8002/ws');
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WebSocketMessage;
      onMessage(data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };
  
  return {
    cleanup: () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    },
    ws
  };
};

// Analytics API
export const getTracksAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/tracks?time_range=${timeRange}`);
  return response.data;
};

export const getArtistsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/artists?time_range=${timeRange}`);
  return response.data;
};

export const getLabelsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/labels?time_range=${timeRange}`);
  return response.data;
};

export const getChannelsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/channels?time_range=${timeRange}`);
  return response.data;
};
