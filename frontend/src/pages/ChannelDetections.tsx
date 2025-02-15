import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Container,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
  TableContainer,
  HStack,
  VStack,
  Text,
  Input,
  Select,
  Button,
  Badge,
  SimpleGrid,
  InputGroup,
  InputLeftElement,
  Flex,
  ButtonGroup,
  FormControl,
  FormLabel,
  useToast
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';

interface Detection {
  id: number;
  station_id: number;
  track_id: number;
  confidence: number;
  detected_at: string;
  play_duration: string;
  track: {
    title: string;
    artist: string;
    isrc?: string;
    label?: string;
    fingerprint?: string;
  };
}

interface StationInfo {
  id: number;
  name: string;
  country: string;
  language: string;
  status: string;
  total_detections: number;
  average_confidence: number;
  total_play_duration: string;
}

interface StationDetails {
  id: number;
  name: string;
  country: string;
  language: string;
  status: string;
  metrics: {
    total_play_time: string;
    detection_count: number;
    unique_tracks: number;
    average_track_duration: string;
    uptime_percentage: number;
  };
  top_tracks: Array<{
    title: string;
    artist: string;
    play_time: string;
    play_count: number;
  }>;
}

interface ApiResponse {
  detections: Detection[];
  total: number;
  page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
  labels: string[];
  station: StationInfo;
}

const ChannelDetections: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [stationDetails, setStationDetails] = useState<StationDetails | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("All Labels");
  const [limit] = useState(10);

  useEffect(() => {
    if (!id) {
      navigate('/channels');
      return;
    }

    const fetchStationDetails = async () => {
      try {
        const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const stationUrl = `${baseUrl}/api/channels/${id}/stats`;
        console.log('Fetching station details from:', stationUrl);
        const response = await fetch(stationUrl);
        if (!response.ok) {
          console.error('Station details error:', response.status, response.statusText);
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Erreur lors de la récupération des détails de la station');
        }
        const details = await response.json();
        console.log('Station Details Response:', details);
        setStationDetails(details);
      } catch (err) {
        console.error('Error fetching station details:', err);
        toast({
          title: "Erreur",
          description: err instanceof Error ? err.message : "Impossible de récupérer les détails de la station",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    };

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const url = new URL(`${baseUrl}/api/channels/${id}/detections`);
        url.searchParams.append('page', currentPage.toString());
        url.searchParams.append('limit', limit.toString());
        if (searchQuery) url.searchParams.append('search', searchQuery);
        if (selectedLabel !== "All Labels") url.searchParams.append('label', selectedLabel);

        console.log('Fetching detections from:', url.toString());
        const response = await fetch(url.toString());
        
        if (!response.ok) {
          console.error('Detections error:', response.status, response.statusText);
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Erreur lors de la récupération des détections');
        }

        const responseData: ApiResponse = await response.json();
        console.log('Detections Response:', responseData);
        setData(responseData);

      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Une erreur est survenue';
        console.error('Fetch Error:', err);
        setError(errorMessage);
        toast({
          title: "Erreur",
          description: errorMessage,
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setLoading(false);
      }
    };

    // Fetch both station details and detections
    Promise.all([fetchStationDetails(), fetchData()]);
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [id, navigate, currentPage, searchQuery, selectedLabel, limit, toast]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  const handleLabelChange = (value: string) => {
    setSelectedLabel(value);
    setCurrentPage(1);
  };

  if (loading && !data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <Spinner size="xl" />
      </Box>
    );
  }

  if (error && !data) {
    return (
      <Container maxW="container.xl" py={4}>
        <RouterLink to="/channels">← Retour à la liste des stations</RouterLink>
        <Alert status="error" mt={4}>
          <AlertIcon />
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={4}>
      <RouterLink to="/channels" style={{ color: '#38A169', fontWeight: 500, marginBottom: '1rem', display: 'inline-block' }}>
        ← Retour à la liste des stations
      </RouterLink>

      {(data?.station || stationDetails) && (
        <>
          <Box bg="green.50" p={4} rounded="lg" mb={4} borderLeft="4px" borderColor="green.500">
            <Heading size="md" mb={2} color="green.700">
              Informations de la station
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              <Box>
                <Text fontWeight="bold" color="green.700">Nom de la station</Text>
                <Text fontSize="lg">{data?.station?.name || stationDetails?.name}</Text>
              </Box>
              <Box>
                <Text fontWeight="bold" color="green.700">Identifiant</Text>
                <Text fontSize="lg">#{data?.station?.id || stationDetails?.id}</Text>
              </Box>
              <Box>
                <Text fontWeight="bold" color="green.700">Pays</Text>
                <Text fontSize="lg">{data?.station?.country || stationDetails?.country || 'Non spécifié'}</Text>
              </Box>
              <Box>
                <Text fontWeight="bold" color="green.700">Langue</Text>
                <Text fontSize="lg">{data?.station?.language || stationDetails?.language || 'Non spécifiée'}</Text>
              </Box>
              <Box>
                <Text fontWeight="bold" color="green.700">Temps total de diffusion</Text>
                <Text fontSize="lg">{stationDetails?.metrics?.total_play_time || data?.station?.total_play_duration}</Text>
              </Box>
              <Box>
                <Text fontWeight="bold" color="green.700">Statut</Text>
                <Badge 
                  colorScheme={(data?.station?.status || stationDetails?.status) === 'active' ? 'green' : 'gray'} 
                  fontSize="md" 
                  px={2} 
                  py={1}
                >
                  {(data?.station?.status || stationDetails?.status || '').toUpperCase()}
                </Badge>
              </Box>
            </SimpleGrid>
          </Box>

          <Box bg="white" rounded="lg" shadow="sm" p={6} mb={6}>
            <SimpleGrid columns={3} spacing={8}>
              <Box p={4} bg="gray.50" rounded="md">
                <Text color="gray.600" fontSize="sm">Total des détections</Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {stationDetails?.metrics?.detection_count || data?.station?.total_detections || 0}
                </Text>
                <Text color="gray.500" fontSize="sm">Depuis le début</Text>
              </Box>
              <Box p={4} bg="gray.50" rounded="md">
                <Text color="gray.600" fontSize="sm">Taux d'activité</Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {stationDetails?.metrics?.uptime_percentage 
                    ? `${Math.round(stationDetails.metrics.uptime_percentage)}%`
                    : 'N/A'}
                </Text>
                <Text color="gray.500" fontSize="sm">Temps en ligne</Text>
              </Box>
              <Box p={4} bg="gray.50" rounded="md">
                <Text color="gray.600" fontSize="sm">Durée moyenne des pistes</Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {stationDetails?.metrics?.average_track_duration || 'N/A'}
                </Text>
                <Text color="gray.500" fontSize="sm">Par détection</Text>
              </Box>
            </SimpleGrid>
          </Box>

          {stationDetails?.top_tracks && stationDetails.top_tracks.length > 0 && (
            <Box bg="white" rounded="lg" shadow="sm" p={6} mb={6}>
              <Heading size="md" mb={4}>Top des pistes</Heading>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Titre</Th>
                    <Th>Artiste</Th>
                    <Th>Temps de lecture</Th>
                    <Th>Nombre de lectures</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {stationDetails.top_tracks.map((track, index) => (
                    <Tr key={index}>
                      <Td>{track.title}</Td>
                      <Td>{track.artist}</Td>
                      <Td>{track.play_time}</Td>
                      <Td>{track.play_count}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}
        </>
      )}

      <Box bg="white" rounded="lg" shadow="sm" p={6}>
        <HStack spacing={4} mb={6}>
          <InputGroup maxW="400px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Rechercher par titre, artiste ou ISRC..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              aria-label="Rechercher des détections"
            />
          </InputGroup>
          <FormControl maxW="200px">
            <FormLabel htmlFor="label-filter">Filtrer par label</FormLabel>
            <Select
              id="label-filter"
              value={selectedLabel}
              onChange={(e) => handleLabelChange(e.target.value)}
              aria-label="Filtrer par label"
              title="Filtrer les détections par label"
            >
              <option value="All Labels">Tous les labels</option>
              {data?.labels?.map(label => (
                <option key={label} value={label}>{label}</option>
              )) || null}
            </Select>
          </FormControl>
        </HStack>

        {loading && (
          <Box display="flex" justifyContent="center" my={4}>
            <Spinner />
          </Box>
        )}

        {error && (
          <Alert status="error" mb={4}>
            <AlertIcon />
            {error}
          </Alert>
        )}

        <TableContainer>
          <Table variant="simple">
            <Thead bg="gray.50">
              <Tr>
                <Th>HORODATAGE</Th>
                <Th>TITRE</Th>
                <Th>ARTISTE</Th>
                <Th>LABEL</Th>
                <Th>ISRC</Th>
                <Th>DURÉE DE LECTURE</Th>
                <Th>CONFIANCE</Th>
              </Tr>
            </Thead>
            <Tbody>
              {data?.detections.map((detection) => (
                <Tr key={detection.id}>
                  <Td whiteSpace="nowrap">{new Date(detection.detected_at).toLocaleString('fr-FR')}</Td>
                  <Td>{detection.track.title}</Td>
                  <Td>{detection.track.artist}</Td>
                  <Td>{detection.track.label || 'N/A'}</Td>
                  <Td>{detection.track.isrc || 'N/A'}</Td>
                  <Td>{detection.play_duration}</Td>
                  <Td>
                    <Badge colorScheme={detection.confidence >= 80 ? 'green' : 'yellow'} variant="solid">
                      {Math.round(detection.confidence)}%
                    </Badge>
                  </Td>
                </Tr>
              ))}
              {!loading && (!data?.detections || data.detections.length === 0) && (
                <Tr>
                  <Td colSpan={7} textAlign="center">
                    {searchQuery || selectedLabel !== "All Labels" 
                      ? "Aucune détection ne correspond aux critères de recherche"
                      : "Aucune détection trouvée"}
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </TableContainer>

        {data?.detections && data.detections.length > 0 && (
          <Flex justify="center" mt={4} gap={2}>
            <ButtonGroup>
              <Button
                size="sm"
                colorScheme="gray"
                onClick={() => handlePageChange(1)}
                isDisabled={currentPage === 1}
              >
                Premier
              </Button>
              <Button
                size="sm"
                colorScheme="gray"
                onClick={() => handlePageChange(currentPage - 1)}
                isDisabled={!data.has_prev}
              >
                Précédent
              </Button>
              <Text alignSelf="center" mx={2}>
                Page {data.page} sur {data.pages}
              </Text>
              <Button
                size="sm"
                colorScheme="gray"
                onClick={() => handlePageChange(currentPage + 1)}
                isDisabled={!data.has_next}
              >
                Suivant
              </Button>
              <Button
                size="sm"
                colorScheme="gray"
                onClick={() => handlePageChange(data.pages)}
                isDisabled={currentPage === data.pages}
              >
                Dernier
              </Button>
            </ButtonGroup>
          </Flex>
        )}
      </Box>
    </Container>
  );
};

export default ChannelDetections;