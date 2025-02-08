import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Grid,
  GridItem,
  Heading,
  Input,
  InputGroup,
  InputLeftElement,
  VStack,
  HStack,
  Badge,
  Link,
  Button,
  IconButton,
  useToast,
  Spinner,
  Text,
  useColorModeValue,
  Icon,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
} from '@chakra-ui/react';
import { SearchIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { FaChartLine, FaPlay, FaPause, FaMusic } from 'react-icons/fa';
import { Link as RouterLink } from 'react-router-dom';
import { fetchStations, detectAudio } from '../services/api';
import { RadioStation } from '../types';
import { WS_URL } from '../config';

const Channels: React.FC = () => {
  const [stations, setStations] = useState<RadioStation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detectingStations, setDetectingStations] = useState<Record<number, boolean>>({});
  const [wsConnected, setWsConnected] = useState(false);
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'track_detection' && data.stream_id) {
        setStations(prev => prev.map(station => {
          if (station.id === data.stream_id) {
            return {
              ...station,
              is_active: true,
              last_detection: {
                title: data.detection.title,
                artist: data.detection.artist,
                confidence: data.detection.confidence,
                detected_at: data.detection.detected_at,
                total_tracks: (station.last_detection?.total_tracks || 0) + 1
              }
            };
          }
          return station;
        }));
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, []);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = handleWebSocketMessage;

    return () => {
      ws.close();
    };
  }, [handleWebSocketMessage]);

  const loadStations = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchStations();
      setStations(data);
      setError(null);
    } catch (error) {
      console.error('Error loading stations:', error);
      setError('Failed to load radio stations');
      toast({
        title: 'Error',
        description: 'Failed to load radio stations',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadStations();
  }, [loadStations]);

  const handleStartDetection = async (stationId: number) => {
    setDetectingStations(prev => ({ ...prev, [stationId]: true }));
    try {
      await detectAudio(stationId);
      toast({
        title: 'Detection Started',
        description: 'Audio detection has been started for this station',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to start audio detection',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setDetectingStations(prev => ({ ...prev, [stationId]: false }));
    }
  };

  const filteredStations = stations.filter(station =>
    station.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    station.language?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    station.country?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <Container centerContent py={8}>
        <Spinner size="xl" />
        <Text mt={4}>Loading radio stations...</Text>
      </Container>
    );
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
            <Button
              colorScheme="red"
              size="sm"
              mt={4}
              onClick={loadStations}
            >
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </Container>
    );
  }

  return (
    <Box p={4}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between">
          <Heading size="lg">Radio Stations</Heading>
          <InputGroup maxW="300px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Search stations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </InputGroup>
        </HStack>

        {!wsConnected && (
          <Alert status="warning">
            <AlertIcon />
            Connection to detection service lost. Real-time updates are not available.
          </Alert>
        )}

        <Grid templateColumns="repeat(auto-fill, minmax(300px, 1fr))" gap={4}>
          {filteredStations.map(station => (
            <GridItem key={station.id}>
              <Box
                p={4}
                bg={bgColor}
                borderRadius="lg"
                borderWidth="1px"
                borderColor={borderColor}
                shadow="sm"
              >
                <VStack align="stretch" spacing={3}>
                  <HStack justify="space-between">
                    <Text fontWeight="bold" noOfLines={1}>
                      {station.name}
                    </Text>
                    <Badge colorScheme={station.is_active ? 'green' : 'red'}>
                      {station.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </HStack>

                  <Box>
                    <Text fontSize="sm" color={textColor}>
                      Country
                    </Text>
                    <Text fontWeight="medium">
                      {station.country || 'Unknown'}
                    </Text>
                  </Box>

                  <Box>
                    <Text fontSize="sm" color={textColor}>
                      Language
                    </Text>
                    <Text fontWeight="medium">
                      {station.language || 'Unknown'}
                    </Text>
                  </Box>

                  {station.last_detection && (
                    <Box>
                      <Text fontSize="sm" color={textColor}>
                        Last Detection
                      </Text>
                      <Text fontWeight="medium">
                        {station.last_detection.title} - {station.last_detection.artist}
                      </Text>
                      <HStack fontSize="sm" color={textColor} spacing={4}>
                        <Text>
                          Confidence: {(station.last_detection.confidence * 100).toFixed(1)}%
                        </Text>
                        <Text>
                          Total Tracks: {station.last_detection.total_tracks}
                        </Text>
                      </HStack>
                    </Box>
                  )}

                  <HStack spacing={2}>
                    <Button
                      colorScheme="brand"
                      size="sm"
                      flex={1}
                      leftIcon={<Icon as={station.is_active ? FaPause : FaPlay} />}
                      onClick={() => handleStartDetection(station.id)}
                      isLoading={detectingStations[station.id]}
                      loadingText="Starting"
                    >
                      {station.is_active ? 'Stop Detection' : 'Start Detection'}
                    </Button>

                    <IconButton
                      aria-label="View detections"
                      icon={<Icon as={FaChartLine} />}
                      size="sm"
                      as={RouterLink}
                      to={`/channels/${station.id}/detections`}
                    />

                    {station.homepage && (
                      <IconButton
                        aria-label="Visit homepage"
                        icon={<ExternalLinkIcon />}
                        size="sm"
                        as={Link}
                        href={station.homepage}
                        target="_blank"
                        rel="noopener noreferrer"
                      />
                    )}
                  </HStack>
                </VStack>
              </Box>
            </GridItem>
          ))}
        </Grid>
      </VStack>
    </Box>
  );
};

export default Channels; 