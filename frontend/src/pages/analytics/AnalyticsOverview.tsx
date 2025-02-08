import React from 'react';
import {
  Box,
  VStack,
  Grid,
  GridItem,
  Text,
  Heading,
  Icon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Flex,
  Select,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { FaCircle } from 'react-icons/fa';

interface ChartData {
  date: string;
  plays: number;
}

interface TopTrack {
  rank: number;
  title: string;
  artist: string;
  label: string;
  isrc: string;
  plays: number;
  playedTime: string;
}

interface TopArtist {
  rank: number;
  name: string;
  plays: number;
  playedTime: string;
}

interface TopLabel {
  rank: number;
  name: string;
  plays: number;
  playedTime: string;
}

interface TopChannel {
  rank: number;
  id: string;
  name: string;
  country: string;
  plays: number;
  playedTime: string;
}

// Sample data for the line chart
const playsData: ChartData[] = [
  { date: '2024-02-01', plays: 150 },
  { date: '2024-02-02', plays: 230 },
  { date: '2024-02-03', plays: 180 },
  { date: '2024-02-04', plays: 290 },
  { date: '2024-02-05', plays: 320 },
  { date: '2024-02-06', plays: 250 },
  { date: '2024-02-07', plays: 400 },
];

// Update the sample data with proper types
const topTracks: TopTrack[] = [
  {
    rank: 1,
    title: "Today's News (Ring It)",
    artist: "Richard John Cartie/KPM Music Ltd",
    label: "APM Music",
    isrc: "GBDL4L081385",
    plays: 127,
    playedTime: "00:55:54"
  },
  {
    rank: 2,
    title: "The Road Future",
    artist: "Fritz Doddy / Jonathan Elias",
    label: "FirstCom Music",
    isrc: "US1ST1653569",
    plays: 92,
    playedTime: "00:20:53"
  }
];

const topArtists: TopArtist[] = [
  {
    rank: 1,
    name: "Richard John Cartie/KPM Music Ltd",
    plays: 127,
    playedTime: "00:54:55"
  },
  {
    rank: 2,
    name: "Fritz Doddy / Jonathan Elias",
    plays: 92,
    playedTime: "00:20:53"
  }
];

const topLabels: TopLabel[] = [
  {
    rank: 1,
    name: "APM Music",
    plays: 173,
    playedTime: "00:55:55"
  },
  {
    rank: 2,
    name: "FirstCom Music",
    plays: 97,
    playedTime: "00:22:29"
  }
];

const topChannels: TopChannel[] = [
  {
    rank: 1,
    id: "258903",
    name: "Radio Future Media 94.0 FM",
    country: "Senegal",
    plays: 1520,
    playedTime: "23:22:33"
  },
  {
    rank: 2,
    id: "246645",
    name: "Sud FM",
    country: "Senegal",
    plays: 891,
    playedTime: "20:52:45"
  }
];

const AnalyticsOverview: React.FC = () => {
  const [dateRange, setDateRange] = React.useState('7d');
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const tooltipBg = useColorModeValue('white', 'gray.800');
  const tooltipColor = useColorModeValue('gray.600', 'gray.400');

  const handleDateRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setDateRange(e.target.value);
  };

  // Formatter functions
  const formatDate = (date: string): string => {
    return new Date(date).toLocaleDateString();
  };

  const formatTooltipLabel = (label: string | number): string => {
    return typeof label === 'string' ? new Date(label).toLocaleDateString() : label.toString();
  };

  const formatTooltipValue = (value: string | number | Array<string | number>): [string | number, string] => {
    const numValue = typeof value === 'number' ? value : 
                    Array.isArray(value) ? Number(value[0]) : 
                    Number(value);
    return [numValue, 'plays'];
  };

  return (
    <VStack spacing={8} align="stretch">
      <Flex justify="flex-end" mb={6}>
        <Select
          value={dateRange}
          onChange={handleDateRangeChange}
          maxW="200px"
          aria-label="Select date range"
          title="Date range filter"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="1y">Last year</option>
        </Select>
      </Flex>

      <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6} mb={8}>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Channels</Text>
            <Heading size="lg" mt={2}>2</Heading>
            <Badge colorScheme="green" mt={2}>Running</Badge>
          </Box>
        </GridItem>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Plays</Text>
            <Heading size="lg" mt={2}>2,786</Heading>
          </Box>
        </GridItem>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Play Time</Text>
            <Heading size="lg" mt={2}>44:15:18</Heading>
          </Box>
        </GridItem>
      </Grid>

      <Box
        p={6}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
        height="400px"
      >
        <Heading size="md" mb={6}>Plays Over Time</Heading>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={playsData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
            />
            <YAxis />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <Box
                      bg={tooltipBg}
                      p={2}
                      borderRadius="md"
                      boxShadow="md"
                      border="1px"
                      borderColor={borderColor}
                    >
                      <Box color={tooltipColor}>
                        <Box fontWeight="medium">{formatTooltipLabel(label)}</Box>
                        <Box>
                          Value: {formatTooltipValue(payload[0].value)}
                        </Box>
                      </Box>
                    </Box>
                  );
                }
                return null;
              }}
            />
            <Line
              type="monotone"
              dataKey="plays"
              stroke="#00853F"
              strokeWidth={2}
              dot={{ fill: '#00853F' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>

      {/* Top Tracks */}
      <Box
        p={6}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Top Tracks</Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Rank</Th>
                <Th>Tendency</Th>
                <Th>Title / Artist</Th>
                <Th>Label / ISRC</Th>
                <Th isNumeric>Plays</Th>
                <Th isNumeric>Played Time</Th>
              </Tr>
            </Thead>
            <Tbody>
              {topTracks.map((track) => (
                <Tr key={track.rank}>
                  <Td>{track.rank}</Td>
                  <Td>
                    <Icon as={FaCircle} color="gray.300" boxSize={3} />
                  </Td>
                  <Td>
                    <Text fontWeight="medium">{track.title}</Text>
                    <Text fontSize="sm" color={textColor}>{track.artist}</Text>
                  </Td>
                  <Td>
                    <Text>{track.label}</Text>
                    <Text fontSize="sm" color={textColor}>{track.isrc}</Text>
                  </Td>
                  <Td isNumeric>{track.plays}</Td>
                  <Td isNumeric>{track.playedTime}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Top Artists */}
      <Box
        p={6}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Top Artists</Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Rank</Th>
                <Th>Tendency</Th>
                <Th>Artist</Th>
                <Th isNumeric>Plays</Th>
                <Th isNumeric>Played Time</Th>
              </Tr>
            </Thead>
            <Tbody>
              {topArtists.map((artist) => (
                <Tr key={artist.rank}>
                  <Td>{artist.rank}</Td>
                  <Td>
                    <Icon as={FaCircle} color="gray.300" boxSize={3} />
                  </Td>
                  <Td>{artist.name}</Td>
                  <Td isNumeric>{artist.plays}</Td>
                  <Td isNumeric>{artist.playedTime}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Top Labels */}
      <Box
        p={6}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Top Labels</Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Rank</Th>
                <Th>Tendency</Th>
                <Th>Label</Th>
                <Th isNumeric>Plays</Th>
                <Th isNumeric>Played Time</Th>
              </Tr>
            </Thead>
            <Tbody>
              {topLabels.map((label) => (
                <Tr key={label.rank}>
                  <Td>{label.rank}</Td>
                  <Td>
                    <Icon as={FaCircle} color="gray.300" boxSize={3} />
                  </Td>
                  <Td>{label.name}</Td>
                  <Td isNumeric>{label.plays}</Td>
                  <Td isNumeric>{label.playedTime}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Top Channels */}
      <Box
        p={6}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Top Channels</Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Rank</Th>
                <Th>Tendency</Th>
                <Th>Channel ID</Th>
                <Th>Channel Name</Th>
                <Th>Country</Th>
                <Th isNumeric>Plays</Th>
                <Th isNumeric>Played Time</Th>
              </Tr>
            </Thead>
            <Tbody>
              {topChannels.map((channel) => (
                <Tr key={channel.rank}>
                  <Td>{channel.rank}</Td>
                  <Td>
                    <Icon as={FaCircle} color="gray.300" boxSize={3} />
                  </Td>
                  <Td>{channel.id}</Td>
                  <Td>{channel.name}</Td>
                  <Td>{channel.country}</Td>
                  <Td isNumeric>{channel.plays}</Td>
                  <Td isNumeric>{channel.playedTime}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>
    </VStack>
  );
};

export default AnalyticsOverview; 