import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  SimpleGrid,
  Tabs,
  TabList,
  TabPanels,
  TabPanel,
  Tab,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Flex,
  Select,
  useColorModeValue,
  Spinner,
  Text,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js';
import { fetchSystemMetrics, fetchDetectionMetrics } from '../services/metrics';

// Enregistrer les composants ChartJS nécessaires
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const Monitoring: React.FC = () => {
  const [timeRange, setTimeRange] = useState<string>('1h');
  const [systemMetrics, setSystemMetrics] = useState<any>(null);
  const [detectionMetrics, setDetectionMetrics] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const lineColor = useColorModeValue('blue.500', 'blue.300');
  const secondaryLineColor = useColorModeValue('green.500', 'green.300');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [systemData, detectionData] = await Promise.all([
          fetchSystemMetrics(timeRange),
          fetchDetectionMetrics(timeRange)
        ]);
        setSystemMetrics(systemData);
        setDetectionMetrics(detectionData);
      } catch (err) {
        console.error('Error fetching metrics:', err);
        setError('Impossible de charger les métriques. Veuillez réessayer plus tard.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Rafraîchir les données toutes les 30 secondes
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value);
  };

  // Options communes pour les graphiques de type Line
  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    },
  };
  
  // Options pour les graphiques de type Bar
  const barChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    },
  };

  // Rendu des graphiques de métriques système
  const renderSystemMetrics = () => {
    if (!systemMetrics) return null;

    const cpuData = {
      labels: systemMetrics.timestamps,
      datasets: [
        {
          label: 'CPU Utilisation (%)',
          data: systemMetrics.cpu_usage,
          borderColor: lineColor,
          backgroundColor: 'rgba(66, 153, 225, 0.2)',
          fill: true,
          tension: 0.4,
        },
      ],
    };

    const memoryData = {
      labels: systemMetrics.timestamps,
      datasets: [
        {
          label: 'Mémoire Utilisée (MB)',
          data: systemMetrics.memory_usage.map((val: number) => val / (1024 * 1024)),
          borderColor: secondaryLineColor,
          backgroundColor: 'rgba(72, 187, 120, 0.2)',
          fill: true,
          tension: 0.4,
        },
      ],
    };

    return (
      <>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={5} mb={5}>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>CPU Moyen</StatLabel>
            <StatNumber>{systemMetrics.avg_cpu.toFixed(2)}%</StatNumber>
            <StatHelpText>Utilisation moyenne du CPU</StatHelpText>
          </Stat>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>Mémoire Moyenne</StatLabel>
            <StatNumber>{(systemMetrics.avg_memory / (1024 * 1024)).toFixed(2)} MB</StatNumber>
            <StatHelpText>Utilisation moyenne de la mémoire</StatHelpText>
          </Stat>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>Temps de Réponse API</StatLabel>
            <StatNumber>{systemMetrics.avg_response_time.toFixed(2)} ms</StatNumber>
            <StatHelpText>Temps de réponse moyen de l'API</StatHelpText>
          </Stat>
        </SimpleGrid>

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={5}>
          <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Utilisation CPU</Heading>
            <Line data={cpuData} options={chartOptions} />
          </Box>
          <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Utilisation Mémoire</Heading>
            <Line data={memoryData} options={chartOptions} />
          </Box>
        </SimpleGrid>
      </>
    );
  };

  // Rendu des graphiques de métriques de détection
  const renderDetectionMetrics = () => {
    if (!detectionMetrics) return null;

    const detectionCountData = {
      labels: detectionMetrics.timestamps,
      datasets: [
        {
          label: 'Nombre de Détections',
          data: detectionMetrics.detection_counts,
          borderColor: lineColor,
          backgroundColor: 'rgba(66, 153, 225, 0.2)',
          fill: true,
          tension: 0.4,
        },
      ],
    };

    const confidenceData = {
      labels: detectionMetrics.timestamps,
      datasets: [
        {
          label: 'Confiance Moyenne (%)',
          data: detectionMetrics.confidence_scores.map((val: number) => val * 100),
          borderColor: secondaryLineColor,
          backgroundColor: 'rgba(72, 187, 120, 0.2)',
          fill: true,
          tension: 0.4,
        },
      ],
    };

    const methodData = {
      labels: ['Local', 'AcoustID', 'AudD'],
      datasets: [
        {
          label: 'Détections par Méthode',
          data: [
            detectionMetrics.detection_by_method.local || 0,
            detectionMetrics.detection_by_method.acoustid || 0,
            detectionMetrics.detection_by_method.audd || 0
          ],
          backgroundColor: [
            'rgba(66, 153, 225, 0.6)',
            'rgba(72, 187, 120, 0.6)',
            'rgba(237, 137, 54, 0.6)',
          ],
        },
      ],
    };

    return (
      <>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={5} mb={5}>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>Total Détections</StatLabel>
            <StatNumber>{detectionMetrics.total_detections}</StatNumber>
            <StatHelpText>Période: {timeRange}</StatHelpText>
          </Stat>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>Confiance Moyenne</StatLabel>
            <StatNumber>{(detectionMetrics.avg_confidence * 100).toFixed(2)}%</StatNumber>
            <StatHelpText>Score de confiance moyen</StatHelpText>
          </Stat>
          <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <StatLabel>Stations Actives</StatLabel>
            <StatNumber>{detectionMetrics.active_stations}</StatNumber>
            <StatHelpText>Stations en cours de surveillance</StatHelpText>
          </Stat>
        </SimpleGrid>

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={5} mb={5}>
          <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Nombre de Détections</Heading>
            <Line data={detectionCountData} options={chartOptions} />
          </Box>
          <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Confiance de Détection</Heading>
            <Line data={confidenceData} options={chartOptions} />
          </Box>
        </SimpleGrid>

        <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>Détections par Méthode</Heading>
          <Bar 
            data={methodData} 
            options={{
              ...barChartOptions,
              indexAxis: 'y' as const,
            }} 
          />
        </Box>
      </>
    );
  };

  return (
    <Container maxW="container.xl" py={4}>
      <Box mb={5}>
        <Flex justify="space-between" align="center" mb={4}>
          <Heading size="lg">Monitoring du Système</Heading>
          <Flex align="center">
            <Text mr={2} fontWeight="medium">Période :</Text>
            <Select
              id="timeRange"
              value={timeRange}
              onChange={handleTimeRangeChange}
              width="150px"
              aria-labelledby="timeRangeLabel"
              title="Sélectionner la plage de temps"
            >
              <option value="1h">Dernière heure</option>
              <option value="6h">6 heures</option>
              <option value="12h">12 heures</option>
              <option value="24h">24 heures</option>
              <option value="7d">7 jours</option>
            </Select>
          </Flex>
        </Flex>

        {error && (
          <Alert status="error" mb={4}>
            <AlertIcon />
            {error}
          </Alert>
        )}

        {loading ? (
          <Flex justify="center" align="center" height="300px">
            <Spinner size="xl" />
          </Flex>
        ) : (
          <Tabs variant="enclosed" colorScheme="brand">
            <TabList>
              <Tab>Vue d'ensemble</Tab>
              <Tab>Système</Tab>
              <Tab>Détection</Tab>
            </TabList>

            <TabPanels>
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={5} mb={5}>
                  {systemMetrics && (
                    <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
                      <Heading size="md" mb={4}>Utilisation CPU</Heading>
                      <Line 
                        data={{
                          labels: systemMetrics.timestamps,
                          datasets: [
                            {
                              label: 'CPU Utilisation (%)',
                              data: systemMetrics.cpu_usage,
                              borderColor: lineColor,
                              backgroundColor: 'rgba(66, 153, 225, 0.2)',
                              fill: true,
                              tension: 0.4,
                            },
                          ],
                        }} 
                        options={chartOptions} 
                      />
                    </Box>
                  )}
                  
                  {detectionMetrics && (
                    <Box height="300px" p={4} bg={bgColor} borderRadius="lg" boxShadow="sm">
                      <Heading size="md" mb={4}>Nombre de Détections</Heading>
                      <Line 
                        data={{
                          labels: detectionMetrics.timestamps,
                          datasets: [
                            {
                              label: 'Nombre de Détections',
                              data: detectionMetrics.detection_counts,
                              borderColor: secondaryLineColor,
                              backgroundColor: 'rgba(72, 187, 120, 0.2)',
                              fill: true,
                              tension: 0.4,
                            },
                          ],
                        }} 
                        options={chartOptions} 
                      />
                    </Box>
                  )}
                </SimpleGrid>

                <SimpleGrid columns={{ base: 1, md: 3 }} spacing={5}>
                  {systemMetrics && (
                    <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
                      <StatLabel>CPU Moyen</StatLabel>
                      <StatNumber>{systemMetrics.avg_cpu.toFixed(2)}%</StatNumber>
                      <StatHelpText>Utilisation moyenne du CPU</StatHelpText>
                    </Stat>
                  )}
                  
                  {detectionMetrics && (
                    <>
                      <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
                        <StatLabel>Total Détections</StatLabel>
                        <StatNumber>{detectionMetrics.total_detections}</StatNumber>
                        <StatHelpText>Période: {timeRange}</StatHelpText>
                      </Stat>
                      
                      <Stat p={3} bg={bgColor} borderRadius="lg" boxShadow="sm">
                        <StatLabel>Stations Actives</StatLabel>
                        <StatNumber>{detectionMetrics.active_stations}</StatNumber>
                        <StatHelpText>Stations en cours de surveillance</StatHelpText>
                      </Stat>
                    </>
                  )}
                </SimpleGrid>
              </TabPanel>

              <TabPanel>
                {renderSystemMetrics()}
              </TabPanel>

              <TabPanel>
                {renderDetectionMetrics()}
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </Box>
    </Container>
  );
};

export default Monitoring; 