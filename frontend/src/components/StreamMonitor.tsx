import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Text,
  VStack,
  HStack,
  Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import { fetchStations } from '../services/api';
import { RadioStation } from '../types';
import { WS_URL } from '../config';
import LoadingSpinner from './LoadingSpinner';

const StreamMonitor: React.FC = () => {
  const [stations, setStations] = useState<RadioStation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    const data = JSON.parse(event.data);
    if (data.type === 'detection_update') {
      setStations(prevStations =>
        prevStations.map(station =>
          station.id === data.station_id
            ? { ...station, last_detection: data.detection }
            : station
        )
      );
    }
  }, []);

  useEffect(() => {
    const loadStations = async () => {
      try {
        setLoading(true);
        const data = await fetchStations();
        setStations(data);
        setError(null);
      } catch (err) {
        console.error('Error loading stations:', err);
        setError('Failed to load stations');
      } finally {
        setLoading(false);
      }
    };

    loadStations();
  }, []);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onmessage = handleWebSocketMessage;
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
    };

    return () => {
      ws.close();
    };
  }, [handleWebSocketMessage]);

  if (loading) return <LoadingSpinner />;
  if (error) return <Text color="red.500">{error}</Text>;

  return (
    <Container maxW="container.xl" py={4}>
      <VStack spacing={4} align="stretch">
        {stations.map((station) => (
          <Box
            key={station.id}
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg={bgColor}
            borderColor={borderColor}
            shadow="sm"
          >
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="bold" fontSize="lg">
                {station.name}
              </Text>
              <Badge colorScheme={station.last_detection ? 'green' : 'gray'}>
                {station.last_detection ? 'Active' : 'Inactive'}
              </Badge>
            </HStack>

            {station.last_detection ? (
              <VStack align="start" spacing={1}>
                <Text>
                  Last Detection: {station.last_detection.title} - {station.last_detection.artist}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Confidence: {(station.last_detection.confidence * 100).toFixed(1)}%
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Total Tracks: {station.last_detection.total_tracks}
                </Text>
              </VStack>
            ) : (
              <Text color="gray.500">No recent detections</Text>
            )}
          </Box>
        ))}
      </VStack>
    </Container>
  );
};

export default StreamMonitor;
