import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  Select,
  Flex,
  useColorModeValue,
  InputGroup,
  InputLeftElement,
  Input,
  Spinner,
  Text,
} from '@chakra-ui/react';
import { FaSearch } from 'react-icons/fa';
import { getLabelsAnalytics } from '../../services/api';
import { formatDuration } from '../../utils/format';

interface Label {
  name: string;
  play_count: number;
  total_play_time: number;
  track_count: number;
  artist_count: number;
}

const AnalyticsLabels: React.FC = () => {
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  const [searchQuery, setSearchQuery] = useState('');
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

  const filteredLabels = labels.filter(label =>
    label.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <Flex justify="center" align="center" h="200px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  return (
    <Box>
      <Flex gap={4} mb={6} direction={{ base: 'column', md: 'row' }}>
        <InputGroup maxW={{ base: "100%", md: "400px" }}>
          <InputLeftElement pointerEvents="none">
            <Icon as={FaSearch} color="gray.400" />
          </InputLeftElement>
          <Input
            placeholder="Search labels..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </InputGroup>

        <Select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          maxW={{ base: "100%", md: "200px" }}
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
              <Th>Label</Th>
              <Th isNumeric>Total Plays</Th>
              <Th isNumeric>Total Play Time</Th>
              <Th isNumeric>Unique Tracks</Th>
              <Th isNumeric>Unique Artists</Th>
            </Tr>
          </Thead>
          <Tbody>
            {filteredLabels.map((label, index) => (
              <Tr key={label.name}>
                <Td>{index + 1}</Td>
                <Td>{label.name}</Td>
                <Td isNumeric>{label.play_count}</Td>
                <Td isNumeric>{formatDuration(label.total_play_time)}</Td>
                <Td isNumeric>{label.track_count}</Td>
                <Td isNumeric>{label.artist_count}</Td>
              </Tr>
            ))}
            {filteredLabels.length === 0 && (
              <Tr>
                <Td colSpan={6} textAlign="center" py={8}>
                  <Text>No labels found for the selected time range</Text>
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