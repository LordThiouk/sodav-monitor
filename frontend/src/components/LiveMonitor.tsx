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
  Tooltip,
  CircularProgress,
  CircularProgressLabel,
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
  FaUser,
  FaHeadphones,
  FaSignal,
  FaChartBar,
  FaList,
  FaRss
} from 'react-icons/fa';
import { fetchStations } from '../services/api';
import { RadioStation } from '../types';
import { WS_URL } from '../config';
import LoadingSpinner from './LoadingSpinner';
import { Link as RouterLink } from 'react-router-dom';
import AnalyticsOverview from './AnalyticsOverview';
import TrackDetectionList from './TrackDetectionList';
import { formatDistanceToNow } from 'date-fns';

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

interface InitialData {
  active_stations: number;
  recent_detections: Detection[];
}

interface WebSocketMessage {
  type: 'initial_data' | 'track_detection' | 'status_update';
  timestamp: string;
  data: any;
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
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const cardBgColor = useColorModeValue('gray.50', 'gray.700');

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        // Load stations
        const stationsData = await fetchStations();
        setStations(stationsData);

        // Load analytics overview for total detections
        const analyticsResponse = await fetch('/api/analytics/overview?time_range=24h');
        if (!analyticsResponse.ok) {
          throw new Error('Failed to fetch analytics data');
        }
        const analyticsData = await analyticsResponse.json();
        setSystemStatus(prev => ({
          ...prev,
          totalDetections: analyticsData.totalPlays || 0,
          activeStations: analyticsData.activeStations || 0,
          totalStations: stationsData.length,
          lastUpdate: new Date().toISOString()
        }));

        // Load latest detections from the database using the new endpoint
        const response = await fetch('/api/detections/latest?limit=10');
        if (!response.ok) {
          throw new Error('Failed to fetch initial detections');
        }
        const data = await response.json();
        const formattedDetections = data.detections.map((d: any) => ({
          id: d.id,
          stationName: d.station_name || d.station?.name || 'Unknown Station',
          title: d.track_title || d.track?.title || 'Unknown Track',
          artist: d.artist || d.track?.artist || 'Unknown Artist',
          isrc: d.track?.isrc || '',
          streamUrl: d.station?.stream_url || '',
          confidence: d.confidence,
          detected_at: d.detected_at,
          play_duration: d.play_duration || '0:00'
        }));
        setLatestDetections(formattedDetections);
        setError(null);
      } catch (error) {
        console.error('Error loading initial data:', error);
        setError('Failed to load initial data');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();

    // Set up periodic refresh of analytics data
    const analyticsRefreshInterval = setInterval(async () => {
      try {
        const analyticsResponse = await fetch('/api/analytics/overview?time_range=24h');
        if (analyticsResponse.ok) {
          const analyticsData = await analyticsResponse.json();
          setSystemStatus(prev => ({
            ...prev,
            totalDetections: analyticsData.totalPlays || 0,
            activeStations: analyticsData.activeStations || 0,
            lastUpdate: new Date().toISOString()
          }));
        }
      } catch (error) {
        console.error('Error refreshing analytics:', error);
      }
    }, 60000); // Refresh every minute

    return () => {
      clearInterval(analyticsRefreshInterval);
    };
  }, []);

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'initial_data':
          const initialData = message.data as InitialData;
          setSystemStatus(prev => ({
            ...prev,
            activeStations: initialData.active_stations,
            totalStations: stations.length,
            lastUpdate: message.timestamp
          }));
          if (latestDetections.length === 0) {
            setLatestDetections(initialData.recent_detections);
          }
          break;

        case 'track_detection':
          const detection = message.data;
          setStationStatus(prev => ({
            ...prev,
            [detection.station_id]: {
              lastUpdate: message.timestamp,
              status: 'active',
              currentTrack: {
                title: detection.track_title,
                artist: detection.artist,
                confidence: detection.confidence,
                detected_at: detection.detected_at
              }
            }
          }));

          // Increment total detections counter
          setSystemStatus(prev => ({
            ...prev,
            totalDetections: prev.totalDetections + 1,
            lastUpdate: message.timestamp
          }));

          // Add new detection to the list
          setLatestDetections(prev => {
            const station = stations.find(s => s.id === detection.station_id);
            
            // Format play_duration consistently
            let formattedDuration = '0:00';
            if (detection.play_duration) {
              // Handle different formats of play_duration
              if (typeof detection.play_duration === 'number') {
                // Convert seconds to mm:ss format
                const minutes = Math.floor(detection.play_duration / 60);
                const seconds = Math.floor(detection.play_duration % 60);
                formattedDuration = `${minutes}:${seconds.toString().padStart(2, '0')}`;
              } else if (typeof detection.play_duration === 'string') {
                // If it's already in mm:ss format, use it directly
                if (detection.play_duration.includes(':')) {
                  formattedDuration = detection.play_duration;
                } else {
                  // Try to parse as number
                  try {
                    const durationSeconds = parseFloat(detection.play_duration);
                    if (!isNaN(durationSeconds)) {
                      const minutes = Math.floor(durationSeconds / 60);
                      const seconds = Math.floor(durationSeconds % 60);
                      formattedDuration = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    }
                  } catch (e) {
                    console.warn('Could not parse play_duration:', detection.play_duration);
                  }
                }
              }
            }
            
            const newDetection = {
              id: detection.id,
              stationName: station?.name || detection.station_name || 'Unknown Station',
              title: detection.track_title,
              artist: detection.artist,
              isrc: detection.track?.isrc || '',
              streamUrl: station?.stream_url || '',
              confidence: detection.confidence,
              detected_at: detection.detected_at,
              play_duration: formattedDuration
            };
            
            const exists = prev.some(d => d.id === newDetection.id);
            if (exists) return prev;
            
            return [newDetection, ...prev].slice(0, 10);
          });
          break;

        case 'status_update':
          setSystemStatus(prev => ({
            ...prev,
            activeStations: message.data.active_stations,
            totalStations: message.data.total_stations,
            totalDetections: message.data.total_detections || prev.totalDetections,
            lastUpdate: message.timestamp
          }));
          break;
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [stations, latestDetections.length]);

  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setError(null);
    };
    
    ws.onmessage = handleWebSocketMessage;
    
    ws.onerror = () => {
      setError('WebSocket connection error. Reconnecting...');
      setTimeout(connectWebSocket, 5000);
    };
    
    ws.onclose = () => {
      console.log('WebSocket closed. Reconnecting...');
      setTimeout(connectWebSocket, 5000);
    };
    
    return ws;
  }, [handleWebSocketMessage]);

  useEffect(() => {
    const ws = connectWebSocket();
    return () => {
      ws.close();
    };
  }, [connectWebSocket]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'green';
    if (confidence >= 70) return 'yellow';
    return 'red';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green';
      case 'inactive': return 'yellow';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

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

  const activeStations = stations.filter(s => s.is_active).length;
  const totalStations = stations.length;
  const uptime = totalStations > 0 ? (activeStations / totalStations) * 100 : 0;

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
        {/* Quick Stats */}
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Active Stations</StatLabel>
                <StatNumber>{systemStatus.activeStations}</StatNumber>
                <StatHelpText>
                  <HStack>
                    <Icon as={FaBroadcastTower} />
                    <Text>{Math.round(uptime)}% Uptime</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Detections</StatLabel>
                <StatNumber>{systemStatus.totalDetections}</StatNumber>
                <StatHelpText>
                  <HStack>
                    <Icon as={FaMusic} />
                    <Text>Tracks detected</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Detection Rate</StatLabel>
                <StatNumber>
                  {(systemStatus.totalDetections / Math.max(1, systemStatus.activeStations)).toFixed(1)}
                </StatNumber>
                <StatHelpText>
                  <HStack>
                    <Icon as={FaChartLine} />
                    <Text>Per station</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>System Status</StatLabel>
                <StatNumber>
                  <HStack>
                    <Icon 
                      as={systemStatus.activeStations > 0 ? FaCheckCircle : FaExclamationTriangle} 
                      color={systemStatus.activeStations > 0 ? "green.500" : "yellow.500"} 
                    />
                    <Text>{systemStatus.activeStations > 0 ? 'Healthy' : 'Warning'}</Text>
                  </HStack>
                </StatNumber>
                <StatHelpText>
                  Updated {formatDistanceToNow(new Date(systemStatus.lastUpdate))} ago
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Quick Access Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Card as={RouterLink} to="/analytics" _hover={{ transform: 'translateY(-2px)', shadow: 'lg' }} transition="all 0.2s">
            <CardBody>
              <HStack spacing={4}>
                <Icon as={FaChartBar} boxSize={8} color="blue.500" />
                <Box>
                  <Heading size="md">Analytics</Heading>
                  <Text color={textColor}>View detailed analytics and reports</Text>
                </Box>
                <Spacer />
                <Icon as={FaArrowRight} />
              </HStack>
            </CardBody>
          </Card>

          <Card as={RouterLink} to="/channels" _hover={{ transform: 'translateY(-2px)', shadow: 'lg' }} transition="all 0.2s">
            <CardBody>
              <HStack spacing={4}>
                <Icon as={FaRss} boxSize={8} color="purple.500" />
                <Box>
                  <Heading size="md">Channels</Heading>
                  <Text color={textColor}>Manage radio stations</Text>
                </Box>
                <Spacer />
                <Icon as={FaArrowRight} />
              </HStack>
            </CardBody>
          </Card>

          <Card as={RouterLink} to="/reports" _hover={{ transform: 'translateY(-2px)', shadow: 'lg' }} transition="all 0.2s">
            <CardBody>
              <HStack spacing={4}>
                <Icon as={FaList} boxSize={8} color="green.500" />
                <Box>
                  <Heading size="md">Reports</Heading>
                  <Text color={textColor}>View all your reports</Text>
                </Box>
                <Spacer />
                <Icon as={FaArrowRight} />
              </HStack>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Latest Detections Preview */}
        <Card>
          <CardHeader>
            <Flex align="center">
              <Heading size="md">Latest Detections</Heading>
              <Spacer />
              <Button as={RouterLink} to="/analytics/tracks" size="sm" rightIcon={<FaArrowRight />}>
                View All
              </Button>
            </Flex>
          </CardHeader>
          <CardBody>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Station</Th>
                    <Th>Track</Th>
                    <Th>Detected</Th>
                    <Th>Confidence</Th>
                    <Th>Duration</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {latestDetections.slice(0, 10).map((detection) => (
                    <Tr key={detection.id}>
                      <Td>
                        <HStack>
                          <Icon as={FaHeadphones} color={textColor} />
                          <Text>{detection.stationName}</Text>
                        </HStack>
                      </Td>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="medium">{detection.title}</Text>
                          <Text fontSize="sm" color={textColor}>{detection.artist}</Text>
                          {detection.isrc && detection.isrc !== 'N/A' && (
                            <HStack spacing={1}>
                              <Icon as={FaMusic} color={textColor} size="xs" />
                              <Text fontSize="xs" color={textColor} fontFamily="mono">
                                ISRC: {detection.isrc}
                              </Text>
                            </HStack>
                          )}
                        </VStack>
                      </Td>
                      <Td>
                        <Tooltip label={new Date(detection.detected_at).toLocaleString()}>
                          <Text>{formatDistanceToNow(new Date(detection.detected_at))} ago</Text>
                        </Tooltip>
                      </Td>
                      <Td>
                        <CircularProgress 
                          value={detection.confidence} 
                          color={getConfidenceColor(detection.confidence)}
                          size="40px"
                        >
                          <CircularProgressLabel>
                            {detection.confidence}%
                          </CircularProgressLabel>
                        </CircularProgress>
                      </Td>
                      <Td>
                        <HStack>
                          <Icon as={FaClock} color={textColor} />
                          <Text>{detection.play_duration}</Text>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                  {latestDetections.length === 0 && (
                    <Tr>
                      <Td colSpan={5} textAlign="center" py={8}>
                        <Text color={textColor}>No detections yet. Waiting for tracks...</Text>
                      </Td>
                    </Tr>
                  )}
                </Tbody>
              </Table>
            </TableContainer>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

export default LiveMonitor;