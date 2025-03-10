// Importation d'axios pour les requêtes HTTP
import axios from 'axios';

// Interface pour les métriques système
export interface SystemMetrics {
  timestamps: string[];
  cpu_usage: number[];
  memory_usage: number[];
  avg_cpu: number;
  avg_memory: number;
  avg_response_time: number;
}

// Interface pour les métriques de détection
export interface DetectionMetrics {
  timestamps: string[];
  detection_counts: number[];
  confidence_scores: number[];
  total_detections: number;
  avg_confidence: number;
  active_stations: number;
  detection_by_method: {
    local: number;
    acoustid: number;
    audd: number;
  };
}

/**
 * Récupère les métriques système du backend
 * @param timeRange Plage de temps pour les métriques (1h, 6h, 12h, 24h, 7d)
 * @returns Métriques système
 */
export const fetchSystemMetrics = async (timeRange: string): Promise<SystemMetrics> => {
  try {
    // Dans un environnement réel, nous ferions un appel API au backend
    // const response = await axios.get(`/api/metrics/system?timeRange=${timeRange}`);
    // return response.data;
    
    // Comme nous n'avons pas de backend Prometheus, nous simulons les données
    return generateMockSystemMetrics(timeRange);
  } catch (error) {
    console.error('Error fetching system metrics:', error);
    throw error;
  }
};

/**
 * Récupère les métriques de détection du backend
 * @param timeRange Plage de temps pour les métriques (1h, 6h, 12h, 24h, 7d)
 * @returns Métriques de détection
 */
export const fetchDetectionMetrics = async (timeRange: string): Promise<DetectionMetrics> => {
  try {
    // Dans un environnement réel, nous ferions un appel API au backend
    // const response = await axios.get(`/api/metrics/detection?timeRange=${timeRange}`);
    // return response.data;
    
    // Comme nous n'avons pas de backend Prometheus, nous simulons les données
    return generateMockDetectionMetrics(timeRange);
  } catch (error) {
    console.error('Error fetching detection metrics:', error);
    throw error;
  }
};

/**
 * Génère des métriques système simulées
 * @param timeRange Plage de temps pour les métriques
 * @returns Métriques système simulées
 */
const generateMockSystemMetrics = (timeRange: string): SystemMetrics => {
  const { timestamps, dataPoints } = generateTimeSeriesData(timeRange);
  
  // Générer des données CPU entre 10% et 80%
  const cpu_usage = Array.from({ length: dataPoints }, () => Math.random() * 70 + 10);
  
  // Générer des données mémoire entre 100MB et 1GB (en bytes)
  const memory_usage = Array.from({ length: dataPoints }, () => (Math.random() * 900 + 100) * 1024 * 1024);
  
  // Calculer les moyennes
  const avg_cpu = cpu_usage.reduce((sum: number, val: number) => sum + val, 0) / cpu_usage.length;
  const avg_memory = memory_usage.reduce((sum: number, val: number) => sum + val, 0) / memory_usage.length;
  
  // Temps de réponse API entre 50ms et 200ms
  const avg_response_time = Math.random() * 150 + 50;
  
  return {
    timestamps,
    cpu_usage,
    memory_usage,
    avg_cpu,
    avg_memory,
    avg_response_time
  };
};

/**
 * Génère des métriques de détection simulées
 * @param timeRange Plage de temps pour les métriques
 * @returns Métriques de détection simulées
 */
const generateMockDetectionMetrics = (timeRange: string): DetectionMetrics => {
  const { timestamps, dataPoints } = generateTimeSeriesData(timeRange);
  
  // Générer des données de détection (nombre de détections par période)
  const detection_counts = Array.from({ length: dataPoints }, () => Math.floor(Math.random() * 50) + 5);
  
  // Générer des scores de confiance entre 0.6 et 1.0
  const confidence_scores = Array.from({ length: dataPoints }, () => Math.random() * 0.4 + 0.6);
  
  // Calculer le total et la moyenne
  const total_detections = detection_counts.reduce((sum: number, val: number) => sum + val, 0);
  const avg_confidence = confidence_scores.reduce((sum: number, val: number) => sum + val, 0) / confidence_scores.length;
  
  // Nombre de stations actives entre 5 et 15
  const active_stations = Math.floor(Math.random() * 10) + 5;
  
  // Répartition des détections par méthode
  const total = Math.floor(Math.random() * 500) + 100;
  const local = Math.floor(total * 0.6); // 60% local
  const acoustid = Math.floor(total * 0.3); // 30% AcoustID
  const audd = total - local - acoustid; // Le reste pour AudD
  
  return {
    timestamps,
    detection_counts,
    confidence_scores,
    total_detections,
    avg_confidence,
    active_stations,
    detection_by_method: {
      local,
      acoustid,
      audd
    }
  };
};

/**
 * Génère des données de séries temporelles en fonction de la plage de temps
 * @param timeRange Plage de temps (1h, 6h, 12h, 24h, 7d)
 * @returns Timestamps et nombre de points de données
 */
const generateTimeSeriesData = (timeRange: string): { timestamps: string[], dataPoints: number } => {
  let dataPoints: number;
  let intervalMinutes: number;
  
  // Déterminer le nombre de points de données et l'intervalle en fonction de la plage de temps
  switch (timeRange) {
    case '1h':
      dataPoints = 12;
      intervalMinutes = 5;
      break;
    case '6h':
      dataPoints = 12;
      intervalMinutes = 30;
      break;
    case '12h':
      dataPoints = 12;
      intervalMinutes = 60;
      break;
    case '24h':
      dataPoints = 24;
      intervalMinutes = 60;
      break;
    case '7d':
      dataPoints = 14;
      intervalMinutes = 60 * 12; // 12 heures
      break;
    default:
      dataPoints = 12;
      intervalMinutes = 5;
  }
  
  // Générer les timestamps
  const now = new Date();
  const timestamps: string[] = [];
  
  for (let i = dataPoints - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * intervalMinutes * 60 * 1000);
    timestamps.push(formatDate(date, timeRange));
  }
  
  return { timestamps, dataPoints };
};

/**
 * Formate une date en fonction de la plage de temps
 * @param date Date à formater
 * @param timeRange Plage de temps
 * @returns Date formatée
 */
const formatDate = (date: Date, timeRange: string): string => {
  if (timeRange === '7d') {
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
  } else if (timeRange === '24h' || timeRange === '12h') {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  } else {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }
}; 