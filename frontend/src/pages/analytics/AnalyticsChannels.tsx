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
  Link,
  useColorModeValue,
} from '@chakra-ui/react';
import { getChannelsAnalytics } from '../../services/api';

interface Channel {
  id: number;
  name: string;
  url: string;
  status: string;
  region: string;
  detection_count: number;
  detection_rate: number;
  total_play_time: string;
  unique_tracks: number;
  tracks: string[];
  unique_artists: number;
  artists: string[];
  unique_labels: number;
  labels: string[];
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
          Channel Analytics
        </Text>
        <Select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          maxW="200px"
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
              <Th>Channel</Th>
              <Th>Region</Th>
              <Th>Status</Th>
              <Th isNumeric>Detections</Th>
              <Th isNumeric>Det/Hour</Th>
              <Th>Total Play Time</Th>
              <Th isNumeric>Artists</Th>
              <Th isNumeric>Tracks</Th>
              <Th isNumeric>Labels</Th>
            </Tr>
          </Thead>
          <Tbody>
            {channels.map((channel) => (
              <Tr key={channel.id}>
                <Td>
                  <Link href={channel.url} isExternal color="blue.500">
                    {channel.name}
                  </Link>
                </Td>
                <Td>{channel.region}</Td>
                <Td>
                  <Badge
                    colorScheme={channel.status === 'active' ? 'green' : 'red'}
                  >
                    {channel.status}
                  </Badge>
                </Td>
                <Td isNumeric>{channel.detection_count}</Td>
                <Td isNumeric>{channel.detection_rate}</Td>
                <Td>{channel.total_play_time}</Td>
                <Td isNumeric>{channel.unique_artists}</Td>
                <Td isNumeric>{channel.unique_tracks}</Td>
                <Td isNumeric>{channel.unique_labels}</Td>
              </Tr>
            ))}
            {channels.length === 0 && (
              <Tr>
                <Td colSpan={9} textAlign="center" py={4}>
                  No channel data available for this time range
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
