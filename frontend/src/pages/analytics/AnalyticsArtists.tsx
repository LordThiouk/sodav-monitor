import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Select,
  Flex,
  Spinner,
  useColorModeValue,
} from '@chakra-ui/react';
import { getArtistsAnalytics } from '../../services/api';

interface Artist {
  artist: string;
  detection_count: number;
  total_play_time: string;
  unique_tracks: number;
  unique_albums: number;
  unique_labels: number;
  unique_stations: number;
}

const AnalyticsArtists: React.FC = () => {
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getArtistsAnalytics(timeRange);
        setArtists(data || []);
      } catch (error) {
        console.error('Error fetching artists analytics:', error);
        setArtists([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange]);

  if (loading) {
    return (
      <Box p={4} display="flex" justifyContent="center">
        <Spinner />
      </Box>
    );
  }

  return (
    <Box p={4}>
      <Flex justify="space-between" align="center" mb={4}>
        <Text fontSize="2xl" fontWeight="bold">
          Artist Analytics
        </Text>
        <Select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          maxW="200px"
          aria-label="Select time range"
          title="Time range selector"
        >
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </Select>
      </Flex>

      <Box overflowX="auto">
        <Table variant="simple" borderWidth={1} borderColor={borderColor}>
          <Thead>
            <Tr>
              <Th>Artist</Th>
              <Th isNumeric>Detections</Th>
              <Th>Total Play Time</Th>
              <Th isNumeric>Unique Tracks</Th>
              <Th isNumeric>Albums</Th>
              <Th isNumeric>Labels</Th>
              <Th isNumeric>Stations</Th>
            </Tr>
          </Thead>
          <Tbody>
            {artists.length > 0 ? (
              artists.map((artist) => (
                <Tr key={artist.artist}>
                  <Td>{artist.artist}</Td>
                  <Td isNumeric>{artist.detection_count}</Td>
                  <Td>{artist.total_play_time}</Td>
                  <Td isNumeric>{artist.unique_tracks}</Td>
                  <Td isNumeric>{artist.unique_albums}</Td>
                  <Td isNumeric>{artist.unique_labels}</Td>
                  <Td isNumeric>{artist.unique_stations}</Td>
                </Tr>
              ))
            ) : (
              <Tr>
                <Td colSpan={7} textAlign="center" py={4}>
                  No artist data available for this time range
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};

export default AnalyticsArtists;