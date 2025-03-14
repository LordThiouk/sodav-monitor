import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  GridItem,
  Stat,
  StatLabel,
  StatNumber,
  VStack,
  Button,
  useToast,
  Spinner,
  Text,
} from '@chakra-ui/react';
import StreamMonitor from '../components/StreamMonitor';
import LoadingSpinner from '../components/LoadingSpinner';
import RadioPlayer from '../components/RadioPlayer';
import { fetchStations, detectAudio, Stream, WebSocketMessage } from '../services/api';
import { RadioStation } from '../types';

interface DashboardStats {
  activeStations: number;
  totalStations: number;
  totalTracks: number;
  lastUpdate: string;
}

interface TrackData {
  station: string;
  tracks: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    activeStations: 0,
    totalStations: 0,
    totalTracks: 0,
    lastUpdate: new Date().toISOString()
  });

  const [trackData, setTrackData] = useState<TrackData[]>([]);
  const [stations, setStations] = useState<RadioStation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [detectingAudio, setDetectingAudio] = useState<{ [key: number]: boolean }>({});
  const toast = useToast();
  const [wsCleanup, setWsCleanup] = useState<{ cleanup: () => void, ws: WebSocket | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        const fetchedStations = await fetchStations();

        const activeStations = fetchedStations.filter(station => station.is_active);
        const totalTracks = fetchedStations.reduce((sum, station) =>
          sum + (station.last_detection?.total_tracks || 0), 0);

        setStats(prev => ({
          ...prev,
          activeStations: activeStations.length,
          totalStations: fetchedStations.length,
          totalTracks,
          lastUpdate: new Date().toISOString()
        }));

        setTrackData(fetchedStations.map(station => ({
          station: station.name,
          tracks: station.last_detection?.total_tracks || 0
        })));

        setStations(fetchedStations);
        setError(null);
      } catch (err) {
        console.error('Error loading dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  const handleDetectAudio = async (streamId: number) => {
    setDetectingAudio(prev => ({ ...prev, [streamId]: true }));
    try {
      const result = await detectAudio(streamId);
      toast({
        title: 'Detection Complete',
        description: `Found track: ${result.detection.title}`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Detection Failed',
        description: 'Failed to detect audio',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setDetectingAudio(prev => ({ ...prev, [streamId]: false }));
    }
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <Text color="red.500">{error}</Text>;
  }

  return (
    <Box p={4}>
      <Grid templateColumns="repeat(auto-fill, minmax(250px, 1fr))" gap={4} mb={8}>
        <GridItem>
          <Stat p={4} bg="white" borderRadius="lg" boxShadow="sm">
            <StatLabel>Active Stations</StatLabel>
            <StatNumber>{stats.activeStations}</StatNumber>
          </Stat>
        </GridItem>
        <GridItem>
          <Stat p={4} bg="white" borderRadius="lg" boxShadow="sm">
            <StatLabel>Total Stations</StatLabel>
            <StatNumber>{stats.totalStations}</StatNumber>
          </Stat>
        </GridItem>
        <GridItem>
          <Stat p={4} bg="white" borderRadius="lg" boxShadow="sm">
            <StatLabel>Total Tracks</StatLabel>
            <StatNumber>{stats.totalTracks}</StatNumber>
          </Stat>
        </GridItem>
      </Grid>

      <VStack spacing={4} align="stretch">
        {stations.map(station => (
          <Box
            key={station.id}
            p={4}
            bg="white"
            borderRadius="lg"
            boxShadow="sm"
          >
            <Grid templateColumns="1fr auto" gap={4} alignItems="center">
              <Box>
                <Text fontWeight="bold">{station.name}</Text>
                <Text fontSize="sm" color="gray.500">
                  {station.language} • {station.country}
                </Text>
              </Box>
              <Button
                colorScheme="blue"
                size="sm"
                onClick={() => handleDetectAudio(station.id)}
                isLoading={detectingAudio[station.id] || false}
                loadingText="Detecting"
              >
                Detect Audio
              </Button>
            </Grid>
          </Box>
        ))}
      </VStack>
    </Box>
  );
};

export default Dashboard;
