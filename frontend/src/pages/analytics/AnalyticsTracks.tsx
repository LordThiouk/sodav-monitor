import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Select,
  Flex,
  Spinner,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useColorModeValue
} from '@chakra-ui/react';
import { getTracksAnalytics } from '../../services/api';
import { TrackAnalytics } from '../../types';

interface AnalyticsTracksProps {}

const AnalyticsTracks: React.FC<AnalyticsTracksProps> = () => {
  const [tracks, setTracks] = useState<TrackAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('7d');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTracksAnalytics(timeRange);
        setTracks(data);
      } catch (error) {
        console.error('Error fetching tracks analytics:', error);
        setError(error instanceof Error ? error.message : 'Failed to fetch tracks');
        setTracks([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange]);

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value);
  };

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" color="blue.500" />
        <Text mt={4}>Loading tracks data...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="lg" m={4}>
        <AlertIcon />
        <AlertTitle mr={2}>Error loading tracks:</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <Box p={4}>
      <Flex justify="flex-end" mb={6}>
        <Select
          value={timeRange}
          onChange={handleTimeRangeChange}
          maxW="200px"
          aria-label="Select time range"
        >
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </Select>
      </Flex>

      <Box overflowX="auto">
        <Table variant="simple" borderWidth="1px" borderColor={borderColor}>
          <Thead>
            <Tr>
              <Th>Title</Th>
              <Th>Artist</Th>
              <Th>Album</Th>
              <Th>Label</Th>
              <Th>ISRC</Th>
              <Th isNumeric>Plays</Th>
              <Th>Total Play Time</Th>
              <Th isNumeric>Unique Stations</Th>
            </Tr>
          </Thead>
          <Tbody>
            {tracks.length > 0 ? (
              tracks.map((track) => (
                <Tr key={track.id}>
                  <Td>{track.title}</Td>
                  <Td>{track.artist}</Td>
                  <Td>{track.album || '-'}</Td>
                  <Td>{track.label || '-'}</Td>
                  <Td>{track.isrc || '-'}</Td>
                  <Td isNumeric>{track.detection_count}</Td>
                  <Td>{track.total_play_time}</Td>
                  <Td isNumeric>{track.unique_stations}</Td>
                </Tr>
              ))
            ) : (
              <Tr>
                <Td colSpan={8} textAlign="center" py={8}>
                  <Text>No tracks found for the selected time range</Text>
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};

export default AnalyticsTracks;