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
} from '@chakra-ui/react';
import { FaMusic, FaExclamationTriangle, FaCheckCircle } from 'react-icons/fa';
import { fetchStations } from '../services/api';
import { RadioStation } from '../types';
import { WS_URL } from '../config';
import LoadingSpinner from './LoadingSpinner';

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

interface SystemStatus {
  activeStations: number;
  totalStations: number;
  totalDetections: number;
  lastUpdate: string;
}

const LiveMonitor: React.FC = () => {
  const [stations, setStations] = useState<RadioStation[]>([]);
  const [stationStatus, setStationStatus] = useState<Record<number, StationStatus>>({});
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    activeStations: 0,
    totalStations: 0,
    totalDetections: 0,
    lastUpdate: new Date().toISOString()
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

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
  }, []);

  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      setReconnectAttempt(0);
    };

    ws.onmessage = handleWebSocketMessage;

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
      
      if (reconnectAttempt < 5) {
        setTimeout(() => {
          setReconnectAttempt(prev => prev + 1);
          connectWebSocket();
        }, 5000);
      }
    };

    return ws;
  }, [handleWebSocketMessage, reconnectAttempt]);

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
    <Container maxW="container.xl" py={4}>
      {!wsConnected && (
        <Alert status="warning" mb={4}>
          <AlertIcon />
          Connection to detection service lost. Attempting to reconnect...
          {reconnectAttempt >= 5 && (
            <Button
              ml={4}
              size="sm"
              onClick={() => {
                setReconnectAttempt(0);
                connectWebSocket();
              }}
            >
              Retry Connection
            </Button>
          )}
        </Alert>
      )}

      <Grid templateColumns="repeat(3, 1fr)" gap={4} mb={6}>
        <GridItem>
          <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <StatLabel>Active Stations</StatLabel>
            <StatNumber>{systemStatus.activeStations}</StatNumber>
            <StatHelpText>
              of {systemStatus.totalStations} total
            </StatHelpText>
            <Progress 
              value={(systemStatus.activeStations / systemStatus.totalStations) * 100} 
              size="sm" 
              colorScheme="green" 
              mt={2}
            />
          </Stat>
        </GridItem>

        <GridItem>
          <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <StatLabel>Total Detections</StatLabel>
            <StatNumber>{systemStatus.totalDetections}</StatNumber>
            <StatHelpText>
              Last updated: {new Date(systemStatus.lastUpdate).toLocaleTimeString()}
            </StatHelpText>
          </Stat>
        </GridItem>

        <GridItem>
          <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <StatLabel>Detection Rate</StatLabel>
            <StatNumber>
              {stations.length > 0
                ? `${Math.round((Object.values(stationStatus).filter(s => s.status === 'active').length / stations.length) * 100)}%`
                : '0%'}
            </StatNumber>
            <StatHelpText>Success rate</StatHelpText>
          </Stat>
        </GridItem>
      </Grid>

      <VStack spacing={4} align="stretch">
        {stations.map(station => {
          const status = stationStatus[station.id];
          const timeSinceLastUpdate = status?.lastUpdate 
            ? Math.round((new Date().getTime() - new Date(status.lastUpdate).getTime()) / 1000)
            : null;

          return (
            <Box
              key={station.id}
              p={4}
              bg={bgColor}
              borderRadius="lg"
              borderWidth="1px"
              borderColor={borderColor}
              shadow="sm"
            >
              <VStack align="stretch" spacing={2}>
                <HStack justify="space-between">
                  <HStack>
                    <Icon
                      as={status?.status === 'error' ? FaExclamationTriangle : 
                          status?.status === 'active' ? FaCheckCircle : FaMusic}
                      color={status?.status === 'active' ? 'green.500' : 
                            status?.status === 'error' ? 'red.500' : 'gray.500'}
                    />
                    <Text fontWeight="bold">{station.name}</Text>
                  </HStack>
                  <Badge
                    colorScheme={
                      status?.status === 'active' ? 'green' :
                      status?.status === 'error' ? 'red' : 'gray'
                    }
                  >
                    {status?.status || 'Unknown'}
                  </Badge>
                </HStack>

                {status?.currentTrack && (
                  <Box>
                    <Text fontSize="sm" color="gray.500">
                      Current Track
                    </Text>
                    <Text fontWeight="medium">
                      {status.currentTrack.title} - {status.currentTrack.artist}
                    </Text>
                    <HStack spacing={4} fontSize="sm" color="gray.500">
                      <Text>
                        Confidence: {(status.currentTrack.confidence * 100).toFixed(1)}%
                      </Text>
                      <Text>
                        Detected: {new Date(status.currentTrack.detected_at).toLocaleTimeString()}
                      </Text>
                    </HStack>
                  </Box>
                )}

                {status?.error && (
                  <Alert status="error" size="sm">
                    <AlertIcon />
                    {status.error}
                  </Alert>
                )}

                {timeSinceLastUpdate !== null && (
                  <Text fontSize="xs" color="gray.500">
                    Last update: {timeSinceLastUpdate < 60 
                      ? `${timeSinceLastUpdate} seconds ago`
                      : `${Math.floor(timeSinceLastUpdate / 60)} minutes ago`}
                  </Text>
                )}
              </VStack>
            </Box>
          );
        })}
      </VStack>
    </Container>
  );
};

export default LiveMonitor; 