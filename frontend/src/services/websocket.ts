import { TrackDetection } from '../types';

type WebSocketInitialData = {
  active_stations: number;
  recent_detections: TrackDetection[];
};

type WebSocketMessage = {
  type: 'initial_data' | 'track_detection' | 'pong';
  timestamp: string;
  data?: WebSocketInitialData | TrackDetection;
};

type WebSocketCallback = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private callbacks: WebSocketCallback[] = [];
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(private url: string = 'ws://localhost:8000/ws') {}

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.startPingInterval();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.callbacks.forEach(callback => callback(message));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.stopPingInterval();
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.ws?.close();
    };
  }

  private startPingInterval() {
    this.pingInterval = setInterval(() => {
      this.ws?.send('ping');
    }, 30000); // Send ping every 30 seconds
  }

  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        console.log('Attempting to reconnect...');
        this.connect();
        this.reconnectTimer = null;
      }, 5000); // Try to reconnect after 5 seconds
    }
  }

  subscribe(callback: WebSocketCallback) {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }

  disconnect() {
    this.stopPingInterval();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
  }
}

export const websocketService = new WebSocketService();
export type { WebSocketMessage, WebSocketInitialData };
