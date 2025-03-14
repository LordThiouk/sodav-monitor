import { RadioStation, Track, TrackDetection, Report, TrackAnalytics } from '../types';
import axios from 'axios';
import { WS_URL } from '../config';

const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://sodav-monitor-production.up.railway.app/api'
  : 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

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
    const data = await response.json();
    return data.detections || [];
  } catch (error) {
    console.error('Error fetching detections:', error);
    return [];
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

export interface ReportResponse {
  id: string;
  title: string;
  type: string;
  format: string;
  generatedAt: string;
  status: string;
  progress?: number;
  downloadUrl?: string;
}

export interface ReportsListResponse {
  reports: ReportResponse[];
}

export interface SubscriptionResponse {
  id: string;
  name: string;
  frequency: string;
  type: string;
  nextDelivery: string;
  recipients: string[];
  active: boolean;
}

export interface SubscriptionsListResponse {
  subscriptions: SubscriptionResponse[];
}

export interface GenerateReportRequest {
  type: string;
  format: string;
  start_date: string;
  end_date: string;
  email?: string;
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
    includeMetadata?: boolean;
  };
  include_graphs?: boolean;
  language?: string;
}

export const fetchReports = async (): Promise<ReportResponse[]> => {
  try {
    const response = await api.get<ReportResponse[]>('/reports');
    return response.data;
  } catch (error) {
    console.error('Error fetching reports:', error);
    return [];
  }
};

export const generateReport = async (reportData: GenerateReportRequest): Promise<ReportResponse> => {
  const response = await api.post('/reports/generate', reportData);
  return response.data;
};

export const getReportSubscriptions = async (): Promise<SubscriptionResponse[]> => {
  try {
    const response = await api.get('/reports/subscriptions');
    return response.data || [];
  } catch (error) {
    console.error('Error fetching subscriptions:', error);
    return [];
  }
};

export const getTracksAnalytics = async (timeRange: string): Promise<TrackAnalytics[]> => {
  try {
    const response = await fetch(`/api/analytics/tracks?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    return data as TrackAnalytics[];
  } catch (error) {
    console.error('Error fetching tracks analytics:', error);
    throw error;
  }
};

export interface WebSocketCleanup {
  cleanup: () => void;
  ws: WebSocket | null;
}

export const connectWebSocket = (onMessage: (data: WebSocketMessage) => void): WebSocketCleanup => {
  const ws = new WebSocket(WS_URL);

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
export const getArtistsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/artists?time_range=${timeRange}`);
  return response.data;
};

export const getLabelsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/labels?time_range=${timeRange}`);
  return response.data.labels;
};

export const getChannelsAnalytics = async (timeRange: string = '7d') => {
  const response = await axios.get(`${API_BASE_URL}/analytics/channels?time_range=${timeRange}`);
  return response.data.channels;
};

export const downloadReport = async (reportId: string) => {
  const response = await api.get(`/reports/${reportId}/download`, {
    responseType: 'blob'
  });
  return response.data;
};

export const createSubscription = async (subscriptionData: {
  name: string;
  type: string;
  frequency: string;
  recipients: string[];
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
  };
}) => {
  const response = await api.post('/reports/subscriptions', subscriptionData);
  return response.data;
};

export const updateSubscription = async (id: string, data: {
  active?: boolean;
  frequency?: string;
  recipients?: string[];
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
  };
}) => {
  const response = await api.patch(`/reports/subscriptions/${id}`, data);
  return response.data;
};

export const deleteSubscription = async (id: string) => {
  const response = await api.delete(`/reports/subscriptions/${id}`);
  return response.data;
};
