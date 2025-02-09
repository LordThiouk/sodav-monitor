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
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { TrackDetection, RadioStation } from '../types';
import { websocketService, WebSocketMessage, WebSocketInitialData } from '../services/websocket';

interface TrackDetectionWithStation extends TrackDetection {
  station?: RadioStation;
}

const TrackDetectionItem: React.FC<{ detection: TrackDetectionWithStation }> = ({ detection }) => {
  const { isOpen, onToggle } = useDisclosure();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const formatDuration = (duration: number): string => {
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

const TrackDetectionList: React.FC = () => {
  const [detections, setDetections] = useState<TrackDetectionWithStation[]>([]);
  const bgColor = useColorModeValue('gray.50', 'gray.900');

  useEffect(() => {
    const unsubscribe = websocketService.subscribe((message: WebSocketMessage) => {
      if (message.type === 'initial_data' && message.data) {
        const initialData = message.data as WebSocketInitialData;
        setDetections(initialData.recent_detections as TrackDetectionWithStation[]);
      } else if (message.type === 'track_detection' && message.data) {
        const newDetection = message.data as TrackDetectionWithStation;
        setDetections(prev => [newDetection, ...prev].slice(0, 50));
      }
    });

    websocketService.connect();

    return () => {
      unsubscribe();
      websocketService.disconnect();
    };
  }, []);

  return (
    <Box>
      <Text fontSize="2xl" fontWeight="bold" mb={4}>
        Live Track Detections
      </Text>
      
      <VStack spacing={4} align="stretch">
        {detections.length === 0 ? (
          <Box
            p={8}
            textAlign="center"
            bg={bgColor}
            borderRadius="lg"
          >
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
