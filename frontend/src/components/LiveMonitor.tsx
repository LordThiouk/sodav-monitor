import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Text,
  VStack,
  HStack,
  Badge,
  useColorModeValue,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Button,
  Grid,
  GridItem,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Progress,
  SimpleGrid,
  Flex,
  Spacer,
  Link,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Divider,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Stack,
  Heading,
  Image,
  Tag,
  TagLabel,
  TagLeftIcon,
} from '@chakra-ui/react';
import { 
  FaMusic, 
  FaExclamationTriangle, 
  FaCheckCircle, 
  FaBroadcastTower, 
  FaArrowRight, 
  FaChartLine,
  FaFileAlt,
  FaCalendarAlt,
  FaClock,
  FaDownload,
  FaBell,
  FaEnvelope,
  FaUser
} from 'react-icons/fa';
import { fetchStations } from '../services/api';
import { RadioStation } from '../types';
import { WS_URL } from '../config';
import LoadingSpinner from './LoadingSpinner';
import { Link as RouterLink } from 'react-router-dom';
import AnalyticsOverview from './AnalyticsOverview';
import TrackDetectionList from './TrackDetectionList';

interface StationStatus {
  lastUpdate: string;
  status: 'active' | 'inactive' | 'error';
  error?: string;
  currentTrack?: {
    title: string;
    artist: string;
    confidence: number;
    detected_at: string;
  };
}

interface Detection {
  id: number;
  stationName: string;
  title: string;
  artist: string;
  isrc: string;
  streamUrl: string;
  confidence: number;
  detected_at: string;
  play_duration: string;
}

interface SystemStatus {
  activeStations: number;
  totalStations: number;
  totalDetections: number;
  lastUpdate: string;
}

interface Report {
  id: string;
  title: string;
  type: string;
  generatedAt: string;
  status: 'completed' | 'pending' | 'failed';
  downloadUrl: string;
  creator: {
    name: string;
    email: string;
  };
}

interface ReportSubscription {
  id: string;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  nextDelivery: string;
  recipients: string[];
  type: string;
}

const LiveMonitor: React.FC = () => {
  const [stations, setStations] = useState<RadioStation[]>([]);
  const [stationStatus, setStationStatus] = useState<Record<number, StationStatus>>({});
  const [latestDetections, setLatestDetections] = useState<Detection[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    activeStations: 0,
    totalStations: 0,
    totalDetections: 0,
    lastUpdate: new Date().toISOString()
  });
  const [lastReport, setLastReport] = useState<Report | null>(null);
  const [activeSubscriptions, setActiveSubscriptions] = useState<ReportSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const cardBgColor = useColorModeValue('gray.50', 'gray.700');

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'status_update':
          setSystemStatus({
            activeStations: data.active_stations,
            totalStations: data.total_stations,
            totalDetections: data.total_detections,
            lastUpdate: data.timestamp
          });
          break;

        case 'track_detection':
          setStationStatus(prev => ({
            ...prev,
            [data.stream_id]: {
              lastUpdate: data.timestamp,
              status: 'active',
              currentTrack: {
                title: data.detection.title,
                artist: data.detection.artist,
                confidence: data.detection.confidence,
                detected_at: data.detection.detected_at
              }
            }
          }));

          // Add to latest detections
          setLatestDetections(prev => {
            const station = stations.find(s => s.id === data.stream_id);
            const newDetection = {
              id: data.detection.id,
              stationName: station?.name || 'Unknown Station',
              title: data.detection.title,
              artist: data.detection.artist,
              isrc: data.detection.isrc || 'N/A',
              streamUrl: station?.stream_url || 'N/A',
              confidence: data.detection.confidence,
              detected_at: data.detection.detected_at,
              play_duration: data.detection.play_duration || '0:00'
            };
            const updated = [newDetection, ...prev].slice(0, 10); // Keep only last 10 detections
            return updated;
          });
          break;

        case 'station_error':
          setStationStatus(prev => ({
            ...prev,
            [data.stream_id]: {
              lastUpdate: data.timestamp,
              status: 'error',
              error: data.error
            }
          }));
          break;
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [stations]);

  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = handleWebSocketMessage;
    return ws;
  }, [handleWebSocketMessage]);

  useEffect(() => {
    const loadStations = async () => {
      try {
        setLoading(true);
        const data = await fetchStations();
        setStations(data);
        setError(null);
      } catch (error) {
        console.error('Error loading stations:', error);
        setError('Failed to load radio stations');
      } finally {
        setLoading(false);
      }
    };

    loadStations();
  }, []);

  useEffect(() => {
    const ws = connectWebSocket();
    return () => {
      ws.close();
    };
  }, [connectWebSocket]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert
          status="error"
          variant="subtle"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          textAlign="center"
          height="200px"
          borderRadius="lg"
        >
          <AlertIcon boxSize="40px" mr={0} />
          <AlertTitle mt={4} mb={1} fontSize="lg">
            Failed to Load Stations
          </AlertTitle>
          <AlertDescription maxWidth="sm">
            {error}
          </AlertDescription>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={5}>
      {error && (
        <Alert status="error" mb={6}>
          <AlertIcon />
          <AlertTitle>Error!</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <VStack spacing={6} align="stretch">
        {/* System Overview */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Stat
            p={4}
            shadow="md"
            border="1px"
            borderColor={borderColor}
            borderRadius="lg"
            bg={bgColor}
          >
            <StatLabel>Active Stations</StatLabel>
            <StatNumber>{stations.filter(s => s.is_active).length}</StatNumber>
            <StatHelpText>
              <Icon as={FaBroadcastTower} mr={1} />
              Currently Broadcasting
            </StatHelpText>
          </Stat>
          
          <Stat
            p={4}
            shadow="md"
            border="1px"
            borderColor={borderColor}
            borderRadius="lg"
            bg={bgColor}
          >
            <StatLabel>Total Stations</StatLabel>
            <StatNumber>{stations.length}</StatNumber>
            <StatHelpText>
              <Icon as={FaMusic} mr={1} />
              Monitored Stations
            </StatHelpText>
          </Stat>
          
          <Stat
            p={4}
            shadow="md"
            border="1px"
            borderColor={borderColor}
            borderRadius="lg"
            bg={bgColor}
          >
            <StatLabel>System Status</StatLabel>
            <StatNumber>
              <Icon 
                as={FaCheckCircle} 
                color="green.500" 
                mr={2}
              />
              Healthy
            </StatNumber>
            <StatHelpText>All Systems Operational</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Live Track Detections */}
        <Box
          p={4}
          shadow="md"
          border="1px"
          borderColor={borderColor}
          borderRadius="lg"
          bg={bgColor}
        >
          <TrackDetectionList />
        </Box>

        {/* Analytics Overview */}
        <Box
          p={4}
          shadow="md"
          border="1px"
          borderColor={borderColor}
          borderRadius="lg"
          bg={bgColor}
        >
          <AnalyticsOverview />
        </Box>
      </VStack>
    </Container>
  );
};

export default LiveMonitor;