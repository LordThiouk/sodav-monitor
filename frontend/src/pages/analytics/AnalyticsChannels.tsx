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
  Badge,
  Spinner,
  useColorModeValue,
} from '@chakra-ui/react';
import { getChannelsAnalytics } from '../../services/api';
import { formatDuration } from '../../utils/format';

interface Channel {
  id: number;
  name: string;
  country?: string;
  language?: string;
  detection_count: number;
  total_play_time: number;
  unique_tracks: number;
  unique_artists: number;
  is_active: boolean;
}

const AnalyticsChannels: React.FC = () => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getChannelsAnalytics(timeRange);
        setChannels(data);
      } catch (error) {
        console.error('Error fetching channels analytics:', error);
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
              <Th>Channel</Th>
              <Th>Country</Th>
              <Th>Language</Th>
              <Th>Status</Th>
              <Th isNumeric>Total Detections</Th>
              <Th isNumeric>Total Play Time</Th>
              <Th isNumeric>Unique Tracks</Th>
              <Th isNumeric>Unique Artists</Th>
            </Tr>
          </Thead>
          <Tbody>
            {channels.map((channel, index) => (
              <Tr key={channel.id}>
                <Td>{index + 1}</Td>
                <Td>{channel.name}</Td>
                <Td>{channel.country || '-'}</Td>
                <Td>{channel.language || '-'}</Td>
                <Td>
                  <Badge
                    colorScheme={channel.is_active ? 'green' : 'red'}
                    variant="subtle"
                  >
                    {channel.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </Td>
                <Td isNumeric>{channel.detection_count}</Td>
                <Td isNumeric>{formatDuration(channel.total_play_time)}</Td>
                <Td isNumeric>{channel.unique_tracks}</Td>
                <Td isNumeric>{channel.unique_artists}</Td>
              </Tr>
            ))}
            {channels.length === 0 && (
              <Tr>
                <Td colSpan={9} textAlign="center" py={8}>
                  <Text>No channels found for the selected time range</Text>
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};

export default AnalyticsChannels; 