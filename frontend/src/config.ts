export const WS_URL = process.env.NODE_ENV === 'production'
  ? 'wss://sodav-monitor-production.up.railway.app/ws'
  : 'ws://localhost:8000/ws';
