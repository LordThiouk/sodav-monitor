import React, { useState, useEffect } from 'react';
import {
  Box,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Text,
  VStack,
  HStack,
  Icon,
  Progress,
  useColorModeValue,
  Card,
  CardBody,
  Heading,
  Flex,
  Spacer,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import {
  FaMusic,
  FaBroadcastTower,
  FaClock,
  FaChartLine,
  FaCalendarAlt,
  FaExclamationTriangle,
  FaCheckCircle,
} from 'react-icons/fa';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface AnalyticsData {
  totalDetections: number;
  detectionRate: number;
  activeStations: number;
  totalStations: number;
  averageConfidence: number;
  detectionsByHour: {
    hour: number;
    count: number;
  }[];
  topArtists: {
    name: string;
    count: number;
  }[];
  systemHealth: {
    status: 'healthy' | 'warning' | 'error';
    uptime: number;
    lastError?: string;
  };
}

const AnalyticsOverview: React.FC = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const chartColor = useColorModeValue('#3182ce', '#63b3ed');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch('/api/analytics/overview');
        if (!response.ok) {
          throw new Error('Failed to fetch analytics data');
        }
        const data = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" color="blue.500" />
        <Text mt={4}>Loading analytics data...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="lg">
        <AlertIcon />
        <AlertTitle>Error loading analytics:</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!analytics) {
    return null;
  }

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / (24 * 3600));
    const hours = Math.floor((seconds % (24 * 3600)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  // Transform data for the chart
  const chartData = analytics.detectionsByHour.map(d => ({
    hour: `${d.hour}:00`,
    detections: d.count
  }));

  return (
    <Box>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={6}>
        {/* Total Detections */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon as={FaMusic} color="blue.500" boxSize={5} />
                <Text fontWeight="medium">Total Detections</Text>
              </HStack>
              <Stat>
                <StatNumber fontSize="3xl">{analytics.totalDetections.toLocaleString()}</StatNumber>
                <StatHelpText>
                  <StatArrow type={analytics.detectionRate > 0 ? "increase" : "decrease"} />
                  {Math.abs(analytics.detectionRate).toFixed(1)}% from previous period
                </StatHelpText>
              </Stat>
            </VStack>
          </CardBody>
        </Card>

        {/* Active Stations */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon as={FaBroadcastTower} color="green.500" boxSize={5} />
                <Text fontWeight="medium">Active Stations</Text>
              </HStack>
              <Stat>
                <StatNumber fontSize="3xl">
                  {analytics.activeStations}/{analytics.totalStations}
                </StatNumber>
                <Progress
                  value={(analytics.activeStations / analytics.totalStations) * 100}
                  size="sm"
                  colorScheme="green"
                  mt={2}
                  width="100%"
                />
              </Stat>
            </VStack>
          </CardBody>
        </Card>

        {/* Average Confidence */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon as={FaChartLine} color="purple.500" boxSize={5} />
                <Text fontWeight="medium">Average Confidence</Text>
              </HStack>
              <Stat>
                <StatNumber fontSize="3xl">
                  {(analytics.averageConfidence * 100).toFixed(1)}%
                </StatNumber>
                <Progress
                  value={analytics.averageConfidence * 100}
                  size="sm"
                  colorScheme={
                    analytics.averageConfidence > 0.8 ? "green" :
                    analytics.averageConfidence > 0.6 ? "yellow" :
                    "red"
                  }
                  mt={2}
                  width="100%"
                />
              </Stat>
            </VStack>
          </CardBody>
        </Card>

        {/* System Health */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon
                  as={analytics.systemHealth.status === 'healthy' ? FaCheckCircle : FaExclamationTriangle}
                  color={
                    analytics.systemHealth.status === 'healthy' ? "green.500" :
                    analytics.systemHealth.status === 'warning' ? "yellow.500" :
                    "red.500"
                  }
                  boxSize={5}
                />
                <Text fontWeight="medium">System Health</Text>
              </HStack>
              <Stat>
                <HStack spacing={2} mb={1}>
                  <Badge
                    colorScheme={
                      analytics.systemHealth.status === 'healthy' ? "green" :
                      analytics.systemHealth.status === 'warning' ? "yellow" :
                      "red"
                    }
                  >
                    {analytics.systemHealth.status.toUpperCase()}
                  </Badge>
                  <Text fontSize="sm" color="gray.500">
                    Uptime: {formatUptime(analytics.systemHealth.uptime)}
                  </Text>
                </HStack>
                {analytics.systemHealth.lastError && (
                  <Text fontSize="sm" color="red.500" mt={2}>
                    {analytics.systemHealth.lastError}
                  </Text>
                )}
              </Stat>
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
        {/* Hourly Detection Trend */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={4}>
              <HStack>
                <Icon as={FaClock} color="blue.500" boxSize={5} />
                <Heading size="sm">Hourly Detection Trend</Heading>
              </HStack>
              <Box width="100%" height="200px">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="detections"
                      stroke={chartColor}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Top Artists */}
        <Card>
          <CardBody>
            <VStack align="start" spacing={4}>
              <HStack>
                <Icon as={FaMusic} color="purple.500" boxSize={5} />
                <Heading size="sm">Top Artists</Heading>
              </HStack>
              <VStack align="stretch" width="100%" spacing={3}>
                {analytics.topArtists.map((artist, index) => (
                  <HStack key={artist.name} justify="space-between">
                    <HStack>
                      <Text color="gray.500" fontSize="sm" width="20px">
                        {index + 1}.
                      </Text>
                      <Text>{artist.name}</Text>
                    </HStack>
                    <Badge colorScheme="purple">{artist.count} plays</Badge>
                  </HStack>
                ))}
              </VStack>
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>
    </Box>
  );
};

export default AnalyticsOverview;
