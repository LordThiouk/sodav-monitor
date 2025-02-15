import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  useColorModeValue,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  Icon,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Select,
  useDisclosure,
  useToast,
  Flex,
  Spacer,
  Spinner,
} from '@chakra-ui/react';
import {
  FaDownload,
  FaCalendarAlt,
  FaEnvelope,
  FaFileAlt,
  FaClock,
  FaPlus,
} from 'react-icons/fa';
import { formatDistanceToNow } from 'date-fns';
import { authenticatedFetch } from '../services/auth';
import { useNavigate, useLocation } from 'react-router-dom';

interface Report {
  id: string;
  title: string;
  type: string;
  format: string;
  generatedAt: string;
  status: 'completed' | 'pending' | 'failed';
  downloadUrl?: string;
}

interface Subscription {
  id: string;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  type: string;
  nextDelivery: string;
  recipients: string[];
}

interface GenerateReportRequest {
  type: string;
  format: string;
  start_date: string;
  end_date: string;
}

const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return 'Unknown date';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Invalid date';
  }
};

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const { isOpen: isSubscriptionOpen, onOpen: onSubscriptionOpen, onClose: onSubscriptionClose } = useDisclosure();
  const { isOpen: isGenerateOpen, onOpen: onGenerateOpen, onClose: onGenerateClose } = useDisclosure();
  const [isGenerating, setIsGenerating] = useState(false);
  const toast = useToast();
  const [newSubscription, setNewSubscription] = useState({
    name: '',
    frequency: 'daily',
    type: 'detection',
    email: '',
  });
  const [newReport, setNewReport] = useState({
    type: 'detection',
    format: 'csv',
    start_date: '',
    end_date: '',
  });
  const navigate = useNavigate();
  const location = useLocation();

  const textColor = useColorModeValue('gray.600', 'gray.400');

  useEffect(() => {
    fetchData();
  }, [toast]);

  const fetchData = async () => {
    try {
      setLoading(true);
      // Fetch reports using authenticated fetch
      const reportsResponse = await authenticatedFetch('/api/reports');
      if (!reportsResponse.ok) {
        if (reportsResponse.status === 401) {
          // Redirect to login if unauthorized
          navigate('/login', { state: { from: location } });
          return;
        }
        throw new Error('Failed to fetch reports');
      }
      const reportsData = await reportsResponse.json();
      // Ensure reports is always an array
      setReports(Array.isArray(reportsData) ? reportsData : []);

      // Fetch subscriptions using authenticated fetch
      const subscriptionsResponse = await authenticatedFetch('/api/reports/subscriptions');
      if (!subscriptionsResponse.ok) {
        if (subscriptionsResponse.status === 401) {
          navigate('/login', { state: { from: location } });
          return;
        }
        throw new Error('Failed to fetch subscriptions');
      }
      const subscriptionsData = await subscriptionsResponse.json();
      // Ensure subscriptions is always an array
      setSubscriptions(Array.isArray(subscriptionsData) ? subscriptionsData : []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: 'Error fetching data',
        description: 'Unable to load reports and subscriptions',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      setReports([]);
      setSubscriptions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      setIsGenerating(true);
      
      // Validate dates
      if (!newReport.start_date || !newReport.end_date) {
        toast({
          title: 'Validation Error',
          description: 'Please select both start and end dates',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
        return;
      }

      const response = await authenticatedFetch('/api/reports', {
        method: 'POST',
        body: JSON.stringify(newReport),
      });

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login', { state: { from: location } });
          return;
        }
        throw new Error('Failed to generate report');
      }

      const data = await response.json();
      toast({
        title: 'Report Generation Started',
        description: 'Your report is being generated. It will appear in the list when ready.',
        status: 'info',
        duration: 5000,
        isClosable: true,
      });

      // Refresh the reports list after a short delay
      setTimeout(fetchData, 2000);
      onGenerateClose();
    } catch (error) {
      console.error('Error generating report:', error);
      toast({
        title: 'Error',
        description: 'Failed to generate report',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (report: Report) => {
    if (!report.downloadUrl) {
      toast({
        title: 'Download not available',
        description: 'Report is not ready for download',
        status: 'warning',
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    try {
      const response = await authenticatedFetch(report.downloadUrl);
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login', { state: { from: location } });
          return;
        }
        throw new Error('Download failed');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}-${report.generatedAt}.${report.format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      toast({
        title: 'Download failed',
        description: 'Unable to download the report',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleCreateSubscription = async () => {
    try {
      const response = await authenticatedFetch('/api/reports/subscriptions', {
        method: 'POST',
        body: JSON.stringify({
          name: newSubscription.name,
          frequency: newSubscription.frequency,
          type: newSubscription.type,
          recipients: [newSubscription.email],
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login', { state: { from: location } });
          return;
        }
        throw new Error('Failed to create subscription');
      }

      const data = await response.json();
      setSubscriptions(prev => [...prev, data]);
      onSubscriptionClose();
      toast({
        title: 'Subscription created',
        description: 'Your report subscription has been created successfully',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create subscription',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'pending':
        return 'yellow';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={4} align="center">
          <Spinner size="xl" />
          <Text>Loading reports and subscriptions...</Text>
        </VStack>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        <HStack justify="space-between">
          <Heading size="lg">Reports & Subscriptions</Heading>
          <Button
            leftIcon={<Icon as={FaPlus} />}
            colorScheme="blue"
            onClick={onSubscriptionOpen}
          >
            New Subscription
          </Button>
        </HStack>

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {/* Recent Reports */}
          <Card>
            <CardHeader>
              <Flex align="center">
                <Heading size="md">Recent Reports</Heading>
                <Spacer />
                <Button
                  size="sm"
                  colorScheme="blue"
                  leftIcon={<Icon as={FaFileAlt} />}
                  onClick={onGenerateOpen}
                >
                  Generate Report
                </Button>
              </Flex>
            </CardHeader>
            <CardBody>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Report</Th>
                    <Th>Generated</Th>
                    <Th>Status</Th>
                    <Th>Action</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {reports.map((report) => (
                    <Tr key={report.id}>
                      <Td>
                        <HStack>
                          <Icon as={FaFileAlt} color={textColor} />
                          <Box>
                            <Text fontWeight="medium">{report.title}</Text>
                            <Text fontSize="sm" color={textColor}>
                              {report.type}
                            </Text>
                          </Box>
                        </HStack>
                      </Td>
                      <Td>
                        <Text>
                          {formatDate(report.generatedAt)}
                        </Text>
                      </Td>
                      <Td>
                        <Badge colorScheme={getStatusColor(report.status)}>
                          {report.status}
                        </Badge>
                      </Td>
                      <Td>
                        <Button
                          size="sm"
                          leftIcon={<Icon as={FaDownload} />}
                          isDisabled={report.status !== 'completed'}
                          onClick={() => handleDownload(report)}
                        >
                          Download
                        </Button>
                      </Td>
                    </Tr>
                  ))}
                  {reports.length === 0 && (
                    <Tr>
                      <Td colSpan={4} textAlign="center" py={8}>
                        <Text color={textColor}>No reports available</Text>
                      </Td>
                    </Tr>
                  )}
                </Tbody>
              </Table>
            </CardBody>
          </Card>

          {/* Active Subscriptions */}
          <Card>
            <CardHeader>
              <Heading size="md">Active Subscriptions</Heading>
            </CardHeader>
            <CardBody>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Name</Th>
                    <Th>Frequency</Th>
                    <Th>Next Delivery</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {subscriptions.map((subscription) => (
                    <Tr key={subscription.id}>
                      <Td>
                        <HStack>
                          <Icon as={FaEnvelope} color={textColor} />
                          <Box>
                            <Text fontWeight="medium">{subscription.name}</Text>
                            <Text fontSize="sm" color={textColor}>
                              {subscription.type} report
                            </Text>
                          </Box>
                        </HStack>
                      </Td>
                      <Td>
                        <HStack>
                          <Icon as={FaCalendarAlt} color={textColor} />
                          <Text>{subscription.frequency}</Text>
                        </HStack>
                      </Td>
                      <Td>
                        <HStack>
                          <Icon as={FaClock} color={textColor} />
                          <Text>
                            {formatDate(subscription.nextDelivery)}
                          </Text>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                  {subscriptions.length === 0 && (
                    <Tr>
                      <Td colSpan={3} textAlign="center" py={8}>
                        <Text color={textColor}>No active subscriptions</Text>
                      </Td>
                    </Tr>
                  )}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </SimpleGrid>
      </VStack>

      {/* New Subscription Modal */}
      <Modal isOpen={isSubscriptionOpen} onClose={onSubscriptionClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Subscription</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Subscription Name</FormLabel>
                <Input
                  placeholder="Daily Detection Report"
                  value={newSubscription.name}
                  onChange={(e) =>
                    setNewSubscription({ ...newSubscription, name: e.target.value })
                  }
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Report Type</FormLabel>
                <Select
                  value={newSubscription.type}
                  onChange={(e) =>
                    setNewSubscription({ ...newSubscription, type: e.target.value })
                  }
                >
                  <option value="detection">Detection Report</option>
                  <option value="analytics">Analytics Report</option>
                  <option value="summary">Summary Report</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Frequency</FormLabel>
                <Select
                  value={newSubscription.frequency}
                  onChange={(e) =>
                    setNewSubscription({
                      ...newSubscription,
                      frequency: e.target.value as 'daily' | 'weekly' | 'monthly',
                    })
                  }
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  placeholder="your@email.com"
                  value={newSubscription.email}
                  onChange={(e) =>
                    setNewSubscription({ ...newSubscription, email: e.target.value })
                  }
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onSubscriptionClose}>
              Cancel
            </Button>
            <Button colorScheme="blue" onClick={handleCreateSubscription}>
              Create Subscription
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Generate Report Modal */}
      <Modal isOpen={isGenerateOpen} onClose={onGenerateClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Generate New Report</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Report Type</FormLabel>
                <Select
                  value={newReport.type}
                  onChange={(e) =>
                    setNewReport({ ...newReport, type: e.target.value })
                  }
                >
                  <option value="detection">Detection Report</option>
                  <option value="analytics">Analytics Report</option>
                  <option value="summary">Summary Report</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Format</FormLabel>
                <Select
                  value={newReport.format}
                  onChange={(e) =>
                    setNewReport({ ...newReport, format: e.target.value })
                  }
                >
                  <option value="csv">CSV</option>
                  <option value="xlsx">Excel</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Start Date</FormLabel>
                <Input
                  type="datetime-local"
                  value={newReport.start_date}
                  onChange={(e) =>
                    setNewReport({ ...newReport, start_date: e.target.value })
                  }
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>End Date</FormLabel>
                <Input
                  type="datetime-local"
                  value={newReport.end_date}
                  onChange={(e) =>
                    setNewReport({ ...newReport, end_date: e.target.value })
                  }
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onGenerateClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleGenerateReport}
              isLoading={isGenerating}
              loadingText="Generating..."
            >
              Generate Report
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};

export default Reports;
