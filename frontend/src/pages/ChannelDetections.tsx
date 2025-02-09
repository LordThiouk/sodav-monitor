import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  HStack,
  Icon,
  IconButton,
  useColorModeValue,
  Heading,
  Button,
  Badge,
  Link,
  Input,
  Select,
  VStack,
  Flex,
  InputGroup,
  InputLeftElement,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Grid,
  GridItem
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { FaSpotify, FaYoutube, FaDeezer, FaSearch, FaSort, FaSortUp, FaSortDown, FaMusic } from 'react-icons/fa';
import { BiTime } from 'react-icons/bi';
import { fetchDetections, fetchStations } from '../services/api';
import { TrackDetection, RadioStation } from '../types';
import { WS_URL } from '../config';
import LoadingSpinner from '../components/LoadingSpinner';

type SortField = 'detected_at' | 'title' | 'artist' | 'label' | 'isrc' | 'play_duration';
type SortOrder = 'asc' | 'desc';

const ChannelDetections: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [station, setStation] = useState<RadioStation | null>(null);
  const [detections, setDetections] = useState<TrackDetection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [labelFilter, setLabelFilter] = useState('all');
  const [sortField, setSortField] = useState<SortField>('detected_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  const itemsPerPage = 10;

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.300');

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'track_detection' && data.stream_id === Number(id)) {
        // Validate and format dates
        const now = new Date().toISOString();
        const detectedAt = data.detection?.detected_at ? new Date(data.detection.detected_at).toISOString() : now;
        
        // Create new detection with proper typing and validated dates
        const newDetection: TrackDetection = {
          id: Date.now(),
          station_id: data.stream_id,
          track_id: Date.now(),
          station_name: station?.name || 'Unknown Station',
          track_title: data.detection.title,
          artist: data.detection.artist,
          detected_at: detectedAt,
          confidence: data.detection.confidence,
          play_duration: data.detection.play_duration ? parseFloat(data.detection.play_duration) : 15,
          track: {
            id: Date.now(),
            title: data.detection.title,
            artist: data.detection.artist,
            isrc: data.detection.isrc || undefined,
            label: data.detection.label || undefined,
            play_count: 1,
            total_play_time: data.detection.play_duration ? parseFloat(data.detection.play_duration) : 15,
            created_at: now,
            last_played: now
          },
          ...(station && { station })
        };

        setDetections(prev => [newDetection, ...prev]);

        // Update station status if needed
        if (station && !station.is_active) {
          setStation({
            ...station,
            is_active: 1,
            last_checked: now
          });
        }
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [id, station]);

  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = handleWebSocketMessage;
    return ws;
  }, [handleWebSocketMessage]);

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        const [stationData, detectionsData] = await Promise.all([
          fetchStations().then(stations => stations.find(s => s.id === Number(id))),
          fetchDetections(Number(id))
        ]);

        if (!stationData) {
          throw new Error('Station not found');
        }

        setStation(stationData);
        setDetections(detectionsData);
        setError(null);
      } catch (error) {
        console.error('Error loading data:', error);
        setError('Failed to load station data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  useEffect(() => {
    const ws = connectWebSocket();
    return () => {
      ws.close();
    };
  }, [connectWebSocket]);

  // Get unique labels for filter dropdown
  const uniqueLabels = React.useMemo(() => {
    const labels = detections
      .map(d => d.track?.label || '')
      .filter(Boolean);
    return ['all', ...Array.from(new Set(labels))];
  }, [detections]);

  // Filter detections
  const filteredDetections = React.useMemo(() => {
    return detections.filter(detection => {
      const matchesSearch = (
        detection.track?.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        detection.track?.artist.toLowerCase().includes(searchQuery.toLowerCase()) ||
        detection.track?.isrc?.toLowerCase().includes(searchQuery.toLowerCase())
      );
      const matchesLabel = labelFilter === 'all' || detection.track?.label === labelFilter;
      return matchesSearch && matchesLabel;
    });
  }, [detections, searchQuery, labelFilter]);

  // Sort detections
  const sortedDetections = React.useMemo(() => {
    return [...filteredDetections].sort((a, b) => {
      let aValue: any = a.detected_at;
      let bValue: any = b.detected_at;

      if (sortField !== 'detected_at') {
        if (sortField === 'title' || sortField === 'artist' || sortField === 'label' || sortField === 'isrc') {
          aValue = a.track?.[sortField] || '';
          bValue = b.track?.[sortField] || '';
        } else {
          aValue = a[sortField];
          bValue = b[sortField];
        }
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }, [filteredDetections, sortField, sortOrder]);

  // Paginate detections
  const paginatedDetections = React.useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return sortedDetections.slice(startIndex, startIndex + itemsPerPage);
  }, [sortedDetections, currentPage]);

  const totalPages = Math.ceil(sortedDetections.length / itemsPerPage);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (field !== sortField) return <Icon as={FaSort} />;
    return sortOrder === 'asc' ? <Icon as={FaSortUp} /> : <Icon as={FaSortDown} />;
  };

  // Add helper function for safe date formatting
  const formatDuration = (seconds: number): string => {
    try {
      if (!seconds || isNaN(seconds)) return '00:00:00';
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    } catch (error) {
      console.error('Error formatting duration:', error);
      return '00:00:00';
    }
  };

  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        throw new Error('Invalid date');
      }
      return date.toLocaleString();
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid date';
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error || !station) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert
          status="error"
          variant="subtle"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          textAlign="center"
          height="200px"
          borderRadius="lg"
        >
          <AlertIcon boxSize="40px" mr={0} />
          <AlertTitle mt={4} mb={1} fontSize="lg">
            Error Loading Station
          </AlertTitle>
          <AlertDescription maxWidth="sm">
            {error || 'Station not found'}
            <Button
              colorScheme="red"
              size="sm"
              mt={4}
              onClick={() => navigate('/channels')}
            >
              Back to Channels
            </Button>
          </AlertDescription>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <Box>
          <Button
            onClick={() => navigate('/channels')}
            variant="ghost"
            size="sm"
            mb={4}
          >
            ← Back to Channels
          </Button>
          
          <Grid templateColumns="repeat(3, 1fr)" gap={4} mb={6}>
            <GridItem colSpan={3}>
              <Box p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
                <HStack spacing={4}>
                  <Icon as={FaMusic} boxSize={8} color="brand.500" />
                  <VStack align="start" spacing={0}>
                    <Heading size="lg">{station.name}</Heading>
                    <Text color={textColor}>
                      ID: {station.id} • {station.country} • {station.language}
                    </Text>
                  </VStack>
                  <Badge
                    ml="auto"
                    colorScheme={station.is_active ? 'green' : 'red'}
                    fontSize="md"
                    px={3}
                    py={1}
                  >
                    {station.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </HStack>
              </Box>
            </GridItem>

            <GridItem>
              <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
                <StatLabel>Total Detections</StatLabel>
                <StatNumber>{detections.length}</StatNumber>
                <StatHelpText>All time</StatHelpText>
              </Stat>
            </GridItem>

            <GridItem>
              <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
                <StatLabel>Average Confidence</StatLabel>
                <StatNumber>
                  {detections.length > 0 ? '100%' : 'N/A'}
                </StatNumber>
                <StatHelpText>Detection accuracy</StatHelpText>
              </Stat>
            </GridItem>

            <GridItem>
              <Stat p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
                <StatLabel>Total Play Duration</StatLabel>
                <StatNumber>
                  {formatDuration(detections.reduce((sum, d) => sum + (d.play_duration || 0), 0))}
                </StatNumber>
                <StatHelpText>Total time songs played</StatHelpText>
              </Stat>
            </GridItem>
          </Grid>
        </Box>

        <VStack spacing={4}>
          <Flex w="100%" gap={4} direction={{ base: 'column', md: 'row' }}>
            <InputGroup maxW={{ base: "100%", md: "400px" }}>
              <InputLeftElement pointerEvents="none">
                <Icon as={FaSearch} color="gray.400" />
              </InputLeftElement>
              <Input
                placeholder="Search by title, artist, or ISRC..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </InputGroup>

            <Select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              maxW={{ base: "100%", md: "200px" }}
              aria-label="Filter by Label"
              title="Filter detections by label"
            >
              {uniqueLabels.map(label => (
                <option key={label} value={label}>
                  {label === 'all' ? 'All Labels' : label}
                </option>
              ))}
            </Select>
          </Flex>
        </VStack>

        <Box
          bg={bgColor}
          borderRadius="lg"
          border="1px"
          borderColor={borderColor}
          overflow="hidden"
        >
          <Box overflowX="auto">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th cursor="pointer" onClick={() => handleSort('detected_at')}>
                    <HStack spacing={2}>
                      <Text>Timestamp</Text>
                      {getSortIcon('detected_at')}
                    </HStack>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('title')}>
                    <HStack spacing={2}>
                      <Text>Title</Text>
                      {getSortIcon('title')}
                    </HStack>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('artist')}>
                    <HStack spacing={2}>
                      <Text>Artist</Text>
                      {getSortIcon('artist')}
                    </HStack>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('label')}>
                    <HStack spacing={2}>
                      <Text>Label</Text>
                      {getSortIcon('label')}
                    </HStack>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('isrc')}>
                    <HStack spacing={2}>
                      <Text>ISRC</Text>
                      {getSortIcon('isrc')}
                    </HStack>
                  </Th>
                  <Th cursor="pointer" onClick={() => handleSort('play_duration')}>
                    <HStack spacing={2}>
                      <Text>Play Duration</Text>
                      {getSortIcon('play_duration')}
                    </HStack>
                  </Th>
                  <Th>Confidence</Th>
                </Tr>
              </Thead>
              <Tbody>
                {paginatedDetections.map((detection) => (
                  <Tr key={detection.id}>
                    <Td whiteSpace="nowrap">
                      <HStack spacing={2}>
                        <Icon as={BiTime} color="gray.500" />
                        <Text>{formatDate(detection.detected_at)}</Text>
                      </HStack>
                    </Td>
                    <Td>{detection.track?.title}</Td>
                    <Td>{detection.track?.artist}</Td>
                    <Td>{detection.track?.label}</Td>
                    <Td>{detection.track?.isrc}</Td>
                    <Td>
                      <HStack spacing={2}>
                        <Icon as={BiTime} color="gray.500" />
                        <Text>{formatDuration(detection.play_duration || 0)}</Text>
                      </HStack>
                    </Td>
                    <Td>
                      <Badge colorScheme="green">
                        100%
                      </Badge>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </Box>

        <Flex justify="center" mt={6} gap={2}>
          <Button
            size="sm"
            onClick={() => setCurrentPage(1)}
            isDisabled={currentPage === 1}
          >
            First
          </Button>
          <Button
            size="sm"
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            isDisabled={currentPage === 1}
          >
            Previous
          </Button>
          <Text alignSelf="center" mx={4}>
            Page {currentPage} of {totalPages}
          </Text>
          <Button
            size="sm"
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            isDisabled={currentPage === totalPages}
          >
            Next
          </Button>
          <Button
            size="sm"
            onClick={() => setCurrentPage(totalPages)}
            isDisabled={currentPage === totalPages}
          >
            Last
          </Button>
        </Flex>
      </VStack>
    </Container>
  );
};

export default ChannelDetections;