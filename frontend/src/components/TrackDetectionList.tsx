import React, { useEffect, useState } from 'react';
import {
  Box,
  VStack,
  Text,
  Badge,
  Grid,
  GridItem,
  IconButton,
  Collapse,
  useColorModeValue,
  HStack,
  useDisclosure,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
  SimpleGrid,
  Heading,
  Divider,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { TrackDetection, RadioStation } from '../types';
import { websocketService, WebSocketMessage, WebSocketInitialData } from '../services/websocket';

interface StationStats {
  station: {
    id: number;
    name: string;
    status: string;
    last_checked: string;
  };
  detections: {
    last_24h: number;
    last_7d: number;
    last_30d: number;
  };
  top_tracks: Array<{
    title: string;
    artist: string;
    plays: number;
    confidence: number;
  }>;
  top_artists: Array<{
    name: string;
    plays: number;
  }>;
  hourly_detections: Array<{
    hour: string;
    count: number;
  }>;
}

interface TrackDetectionWithStation extends TrackDetection {
  station?: RadioStation;
}

const StationStatsDisplay: React.FC<{ stats: StationStats }> = ({ stats }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box mb={6} p={4} bg={bgColor} borderWidth="1px" borderColor={borderColor} borderRadius="lg" shadow="sm">
      <VStack spacing={4} align="stretch">
        <Heading size="md">{stats.station.name} - Statistics</Heading>

        <StatGroup>
          <Stat>
            <StatLabel>Last 24h</StatLabel>
            <StatNumber>{stats.detections.last_24h}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Last 7 days</StatLabel>
            <StatNumber>{stats.detections.last_7d}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Last 30 days</StatLabel>
            <StatNumber>{stats.detections.last_30d}</StatNumber>
          </Stat>
        </StatGroup>

        <Divider />

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          <Box>
            <Heading size="sm" mb={2}>Top Tracks (24h)</Heading>
            <VStack align="stretch" spacing={2}>
              {stats.top_tracks.slice(0, 5).map((track, index) => (
                <HStack key={index} justify="space-between">
                  <Text fontSize="sm">{track.title} - {track.artist}</Text>
                  <Badge colorScheme="green">{track.plays} plays</Badge>
                </HStack>
              ))}
            </VStack>
          </Box>

          <Box>
            <Heading size="sm" mb={2}>Top Artists (24h)</Heading>
            <VStack align="stretch" spacing={2}>
              {stats.top_artists.slice(0, 5).map((artist, index) => (
                <HStack key={index} justify="space-between">
                  <Text fontSize="sm">{artist.name}</Text>
                  <Badge colorScheme="purple">{artist.plays} plays</Badge>
                </HStack>
              ))}
            </VStack>
          </Box>
        </SimpleGrid>
      </VStack>
    </Box>
  );
};

const TrackDetectionItem: React.FC<{ detection: TrackDetectionWithStation }> = ({ detection }) => {
  const { isOpen, onToggle } = useDisclosure();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const formatDuration = (duration: number | string | null | undefined): string => {
    // Handle null or undefined
    if (duration === null || duration === undefined) {
      return '0:00';
    }

    // Handle string format (could be "mm:ss" or a number as string)
    if (typeof duration === 'string') {
      // Check if it's already in mm:ss format
      if (duration.includes(':')) {
        return duration;
      }

      // Try to parse as number
      const parsed = parseFloat(duration);
      if (isNaN(parsed)) {
        return '0:00';
      }
      duration = parsed;
    }

    // Now duration is definitely a number
    if (duration < 0) {
      return '0:00';
    }

    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence > 80) return 'green';
    if (confidence > 60) return 'yellow';
    return 'orange';
  };

  return (
    <Box
      p={4}
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="lg"
      shadow="sm"
      mb={2}
    >
      <Grid templateColumns="1fr auto auto" gap={4} alignItems="center">
        <GridItem>
          <VStack align="start" spacing={1}>
            <Text fontWeight="bold" fontSize="lg">
              {detection.track?.title || 'Unknown Title'}
            </Text>
            <Text color="gray.500">
              {detection.track?.artist || 'Unknown Artist'}
            </Text>
          </VStack>
        </GridItem>

        <GridItem>
          <Badge
            colorScheme={getConfidenceColor(detection.confidence)}
            fontSize="sm"
            px={2}
            py={1}
            borderRadius="full"
          >
            {Math.round(detection.confidence)}% Match
          </Badge>
        </GridItem>

        <GridItem>
          <IconButton
            aria-label="Toggle details"
            icon={isOpen ? <ChevronUpIcon /> : <ChevronDownIcon />}
            onClick={onToggle}
            variant="ghost"
            size="sm"
          />
        </GridItem>
      </Grid>

      <Collapse in={isOpen}>
        <Box mt={4} pl={4}>
          <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap={4}>
            <VStack align="start" spacing={2}>
              <HStack>
                <Text fontWeight="semibold">Album:</Text>
                <Text>{detection.track?.album || 'N/A'}</Text>
              </HStack>
              <HStack>
                <Text fontWeight="semibold">ISRC:</Text>
                <Text fontFamily="mono">{detection.track?.isrc || 'N/A'}</Text>
              </HStack>
              <HStack>
                <Text fontWeight="semibold">Label:</Text>
                <Text>{detection.track?.label || 'N/A'}</Text>
              </HStack>
            </VStack>

            <VStack align="start" spacing={2}>
              <HStack>
                <Text fontWeight="semibold">Station:</Text>
                <Text>{detection.station?.name || 'Unknown Station'}</Text>
              </HStack>
              <HStack>
                <Text fontWeight="semibold">Duration:</Text>
                <Text>{formatDuration(detection.play_duration)}</Text>
              </HStack>
              <HStack>
                <Text fontWeight="semibold">Detected:</Text>
                <Text>{new Date(detection.detected_at).toLocaleString()}</Text>
              </HStack>
            </VStack>
          </Grid>
        </Box>
      </Collapse>
    </Box>
  );
};

const TrackDetectionList: React.FC<{ stationId?: number }> = ({ stationId }) => {
  const [detections, setDetections] = useState<TrackDetectionWithStation[]>([]);
  const [stationStats, setStationStats] = useState<StationStats | null>(null);
  const bgColor = useColorModeValue('gray.50', 'gray.900');

  useEffect(() => {
    // Fetch station stats if stationId is provided
    const fetchStationStats = async () => {
      if (stationId) {
        try {
          const response = await fetch(`/api/stations/${stationId}/stats`);
          if (response.ok) {
            const data = await response.json();
            setStationStats(data);
          }
        } catch (error) {
          console.error('Error fetching station stats:', error);
        }
      }
    };

    fetchStationStats();

    const unsubscribe = websocketService.subscribe((message: WebSocketMessage) => {
      if (message.type === 'initial_data' && message.data) {
        const initialData = message.data as WebSocketInitialData;
        const filteredDetections = stationId
          ? initialData.recent_detections.filter(d => d.station_id === stationId)
          : initialData.recent_detections;
        setDetections(filteredDetections as TrackDetectionWithStation[]);
      } else if (message.type === 'track_detection' && message.data) {
        const newDetection = message.data as TrackDetectionWithStation;
        if (!stationId || newDetection.station_id === stationId) {
          setDetections(prev => [newDetection, ...prev].slice(0, 50));
          // Refresh station stats when new detection arrives
          fetchStationStats();
        }
      }
    });

    websocketService.connect();

    return () => {
      unsubscribe();
      websocketService.disconnect();
    };
  }, [stationId]);

  return (
    <Box>
      {stationStats && <StationStatsDisplay stats={stationStats} />}

      <Text fontSize="2xl" fontWeight="bold" mb={4}>
        Live Track Detections
      </Text>

      <VStack spacing={4} align="stretch">
        {detections.length === 0 ? (
          <Box p={8} textAlign="center" bg={bgColor} borderRadius="lg">
            <Text color="gray.500">
              No track detections yet. Waiting for new tracks...
            </Text>
          </Box>
        ) : (
          detections.map((detection) => (
            <TrackDetectionItem
              key={`${detection.station_id}-${detection.detected_at}`}
              detection={detection}
            />
          ))
        )}
      </VStack>
    </Box>
  );
};

export default TrackDetectionList;
