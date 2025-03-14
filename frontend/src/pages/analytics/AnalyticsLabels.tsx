import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Flex,
  useColorModeValue,
  Select,
  Text,
  Spinner,
} from '@chakra-ui/react';
import { getLabelsAnalytics } from '../../services/api';

interface Label {
  label: string;
  detection_count: number;
  total_play_time: string;
  unique_tracks: number;
  tracks: string[];
  unique_artists: number;
  artists: string[];
  unique_albums: number;
  albums: string[];
  unique_stations: number;
  stations: string[];
}

const AnalyticsLabels: React.FC = () => {
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getLabelsAnalytics(timeRange);
        setLabels(data);
      } catch (error) {
        console.error('Error fetching labels analytics:', error);
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
          Label Analytics
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
              <Th>Label</Th>
              <Th isNumeric>Detections</Th>
              <Th>Total Play Time</Th>
              <Th isNumeric>Artists</Th>
              <Th isNumeric>Tracks</Th>
              <Th isNumeric>Albums</Th>
              <Th isNumeric>Stations</Th>
            </Tr>
          </Thead>
          <Tbody>
            {labels.map((label) => (
              <Tr key={label.label}>
                <Td>{label.label}</Td>
                <Td isNumeric>{label.detection_count}</Td>
                <Td>{label.total_play_time}</Td>
                <Td isNumeric>{label.unique_artists}</Td>
                <Td isNumeric>{label.unique_tracks}</Td>
                <Td isNumeric>{label.unique_albums}</Td>
                <Td isNumeric>{label.unique_stations}</Td>
              </Tr>
            ))}
            {labels.length === 0 && (
              <Tr>
                <Td colSpan={7} textAlign="center" py={4}>
                  No label data available for this time range
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};

export default AnalyticsLabels;
