import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Grid,
  GridItem,
  Select,
  Flex,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// API Response Interfaces
interface ChartData {
  hour: string;
  count: number;
}

interface TopTrack {
  rank: number;
  title: string;
  artist: string;
  plays: number;
  duration: string;
}

interface TopArtist {
  rank: number;
  name: string;
  plays: number;
}

interface SystemHealth {
  status: string;
  uptime: number;
  lastError: string | null;
}

interface AnalyticsData {
  totalChannels: number;
  activeStations: number;
  totalPlays: number;
  totalPlayTime: string;
  playsData: ChartData[];
  topTracks: TopTrack[];
  topArtists: TopArtist[];
  systemHealth: SystemHealth;
  topLabels: TransformedLabel[];
  topChannels: TransformedChannel[];
}

// UI Data Interfaces
interface TransformedChartData {
  date: string;
  plays: number;
}

interface TransformedTrack {
  rank: number;
  title: string;
  artist: string;
  plays: number;
  duration: string;
  id: string;
}

interface TransformedArtist {
  rank: number;
  name: string;
  plays: number;
}

interface TransformedLabel {
  rank: number;
  name: string;
  plays: number;
}

interface TransformedChannel {
  rank: number;
  name: string;
  region: string;
  plays: number;
}

interface TransformedData {
  totalChannels: number;
  activeChannels: number;
  totalPlays: number;
  totalPlayTime: string;
  playsData: TransformedChartData[];
  topTracks: TransformedTrack[];
  topArtists: TransformedArtist[];
  topLabels: TransformedLabel[];
  topChannels: TransformedChannel[];
}

const AnalyticsOverview: React.FC = () => {
  const [dateRange, setDateRange] = useState('7d');
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  const handleDateRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setDateRange(e.target.value);
  };

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/analytics/overview?time_range=${dateRange}`);
        if (!response.ok) {
          throw new Error('Failed to fetch analytics data');
        }
        const data: AnalyticsData = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching analytics:', error);
        setError(error instanceof Error ? error.message : 'An error occurred while fetching analytics data');
        setAnalytics(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [dateRange]);

  // Transform data for display
  const transformedData: TransformedData = analytics ? {
    totalChannels: analytics.totalChannels || 0,
    activeChannels: analytics.activeStations || 0,
    totalPlays: analytics.totalPlays || 0,
    totalPlayTime: analytics.totalPlayTime || '00:00:00',
    playsData: analytics.playsData?.map(d => ({ 
      date: new Date(d.hour).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), 
      plays: d.count || 0 
    })) || [],
    topTracks: (analytics.topTracks || []).map(track => ({
      ...track,
      id: `track-${track.rank}`
    })),
    topArtists: analytics.topArtists || [],
    topLabels: analytics.topLabels || [],
    topChannels: analytics.topChannels || []
  } : {
    totalChannels: 0,
    activeChannels: 0,
    totalPlays: 0,
    totalPlayTime: '00:00:00',
    playsData: [],
    topTracks: [],
    topArtists: [],
    topLabels: [],
    topChannels: []
  };

  const data = transformedData;

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <Spinner size="xl" color="blue.500" />
      </Flex>
    );
  }

  return (
    <VStack spacing={8} align="stretch">
      {error && (
        <Alert status="error" borderRadius="lg" mb={4}>
          <AlertIcon />
          <AlertTitle>Error loading analytics:</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Flex justify="flex-end" mb={6}>
        <FormControl id="dateRange" w="auto">
          <FormLabel srOnly>Select date range</FormLabel>
          <Select
            value={dateRange}
            onChange={handleDateRangeChange}
            width="auto"
            ml={4}
            aria-label="Select date range"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </Select>
        </FormControl>
      </Flex>

      <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6}>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Channels</Text>
            <Heading size="lg" mt={2}>{data.totalChannels}</Heading>
            <Text fontSize="sm" color={textColor} mt={2}>
              {data.activeChannels} channels currently active
            </Text>
            <Badge colorScheme={data.activeChannels > 0 ? "green" : "gray"} mt={2}>
              {data.activeChannels} Active / {data.totalChannels} Total
            </Badge>
          </Box>
        </GridItem>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Plays</Text>
            <Heading size="lg" mt={2}>{data.totalPlays.toLocaleString()}</Heading>
            <Text fontSize="sm" color={textColor} mt={2}>
              In the last {dateRange === '24h' ? '24 hours' : dateRange === '7d' ? '7 days' : dateRange === '30d' ? '30 days' : '90 days'}
            </Text>
          </Box>
        </GridItem>
        <GridItem>
          <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
            <Text fontSize="sm" color={textColor}>Total Play Time</Text>
            <Heading size="lg" mt={2}>{data.totalPlayTime}</Heading>
            <Text fontSize="sm" color={textColor} mt={2}>
              Hours:Minutes:Seconds
            </Text>
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
          <LineChart data={data.playsData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="plays"
              stroke="#3182ce"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>

      <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={6}>
        <GridItem>
          <Box
            p={6}
            bg={bgColor}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={borderColor}
          >
            <Heading size="md" mb={6}>Top Tracks</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Track</Th>
                  <Th isNumeric>Plays</Th>
                  <Th>Duration</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data?.topTracks && data.topTracks.length > 0 ? data.topTracks.map((track) => (
                  <Tr key={track.id}>
                    <Td>{track.rank}</Td>
                    <Td>
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="medium">{track.title}</Text>
                        <Text fontSize="sm" color={textColor}>{track.artist}</Text>
                      </VStack>
                    </Td>
                    <Td isNumeric>{track.plays}</Td>
                    <Td>{track.duration}</Td>
                  </Tr>
                )) : (
                  <Tr>
                    <Td colSpan={4} textAlign="center">No tracks available</Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </GridItem>

        <GridItem>
          <Box
            p={6}
            bg={bgColor}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={borderColor}
          >
            <Heading size="md" mb={6}>Top Artists</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Artist</Th>
                  <Th isNumeric>Plays</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data?.topArtists && data.topArtists.length > 0 ? data.topArtists.map((artist) => (
                  <Tr key={artist.rank}>
                    <Td>{artist.rank}</Td>
                    <Td>{artist.name}</Td>
                    <Td isNumeric>{artist.plays}</Td>
                  </Tr>
                )) : (
                  <Tr>
                    <Td colSpan={3} textAlign="center">No artists available</Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </GridItem>

        <GridItem>
          <Box
            p={6}
            bg={bgColor}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={borderColor}
          >
            <Heading size="md" mb={6}>Top Labels</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Label</Th>
                  <Th isNumeric>Plays</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data?.topLabels && data.topLabels.length > 0 ? data.topLabels.map((label) => (
                  <Tr key={label.rank}>
                    <Td>{label.rank}</Td>
                    <Td>{label.name}</Td>
                    <Td isNumeric>{label.plays}</Td>
                  </Tr>
                )) : (
                  <Tr>
                    <Td colSpan={3} textAlign="center">No labels available</Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </GridItem>

        <GridItem>
          <Box
            p={6}
            bg={bgColor}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={borderColor}
          >
            <Heading size="md" mb={6}>Top Channels</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Channel</Th>
                  <Th>Region</Th>
                  <Th isNumeric>Plays</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data?.topChannels && data.topChannels.length > 0 ? data.topChannels.map((channel) => (
                  <Tr key={channel.rank}>
                    <Td>{channel.rank}</Td>
                    <Td>{channel.name}</Td>
                    <Td>{channel.region}</Td>
                    <Td isNumeric>{channel.plays}</Td>
                  </Tr>
                )) : (
                  <Tr>
                    <Td colSpan={4} textAlign="center">No channels available</Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </GridItem>
      </Grid>

      
    </VStack>
  );
};

export default AnalyticsOverview;