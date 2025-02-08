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
import { getTracksAnalytics } from '../../services/api';
import { formatDuration } from '../../utils/format';

interface Track {
  id: number;
  title: string;
  artist: string;
  album?: string;
  label?: string;
  duration?: number;
  play_count: number;
  total_play_time: number;
  last_played?: string;
}

const AnalyticsTracks: React.FC = () => {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getTracksAnalytics(timeRange);
        setTracks(data);
      } catch (error) {
        console.error('Error fetching tracks analytics:', error);
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
              <Th>Title</Th>
              <Th>Artist</Th>
              <Th>Album</Th>
              <Th>Label</Th>
              <Th isNumeric>Duration</Th>
              <Th isNumeric>Plays</Th>
              <Th isNumeric>Total Play Time</Th>
              <Th>Last Played</Th>
            </Tr>
          </Thead>
          <Tbody>
            {tracks.map((track, index) => (
              <Tr key={track.id}>
                <Td>{index + 1}</Td>
                <Td>{track.title}</Td>
                <Td>{track.artist}</Td>
                <Td>{track.album || '-'}</Td>
                <Td>{track.label || '-'}</Td>
                <Td isNumeric>{track.duration ? formatDuration(track.duration) : '-'}</Td>
                <Td isNumeric>{track.play_count}</Td>
                <Td isNumeric>{formatDuration(track.total_play_time)}</Td>
                <Td>
                  {track.last_played
                    ? new Date(track.last_played).toLocaleString()
                    : '-'}
                </Td>
              </Tr>
            ))}
            {tracks.length === 0 && (
              <Tr>
                <Td colSpan={9} textAlign="center" py={8}>
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