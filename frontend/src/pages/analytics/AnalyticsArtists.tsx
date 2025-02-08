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
import { formatDuration } from '../../utils/format';

interface Artist {
  name: string;
  play_count: number;
  total_play_time: number;
  track_count: number;
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
        setArtists(data);
      } catch (error) {
        console.error('Error fetching artists analytics:', error);
      }
      setLoading(false);
    };

    fetchData();
  }, [timeRange]);

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value);
  };

  if (loading) {
    return (
      <Flex justify="center" align="center" h="200px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  return (
    <Box>
      <Flex justify="flex-end" mb={6}>
        <Select
          value={timeRange}
          onChange={handleTimeRangeChange}
          maxW="200px"
          aria-label="Select time range"
          title="Time range filter"
        >
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="1y">Last year</option>
        </Select>
      </Flex>

      <Box overflowX="auto">
        <Table variant="simple" borderWidth="1px" borderColor={borderColor}>
          <Thead>
            <Tr>
              <Th>Rank</Th>
              <Th>Artist</Th>
              <Th isNumeric>Total Plays</Th>
              <Th isNumeric>Total Play Time</Th>
              <Th isNumeric>Unique Tracks</Th>
              <Th isNumeric>Avg. Plays per Track</Th>
            </Tr>
          </Thead>
          <Tbody>
            {artists.map((artist, index) => (
              <Tr key={artist.name}>
                <Td>{index + 1}</Td>
                <Td>{artist.name}</Td>
                <Td isNumeric>{artist.play_count}</Td>
                <Td isNumeric>{formatDuration(artist.total_play_time)}</Td>
                <Td isNumeric>{artist.track_count}</Td>
                <Td isNumeric>
                  {(artist.play_count / artist.track_count).toFixed(1)}
                </Td>
              </Tr>
            ))}
            {artists.length === 0 && (
              <Tr>
                <Td colSpan={6} textAlign="center" py={8}>
                  <Text>No artists found for the selected time range</Text>
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