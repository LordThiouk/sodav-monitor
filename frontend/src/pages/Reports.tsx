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
  Flex,
  FormControl,
  FormLabel,
  Input,
  Select,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Switch,
  Progress,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Icon,
  useToast
} from '@chakra-ui/react';
import { FaDownload, FaEdit, FaTrash, FaPlus } from 'react-icons/fa';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  generateReport,
  downloadReport,
  getReportSubscriptions,
  createSubscription,
  updateSubscription,
  deleteSubscription,
  fetchReports,
  ReportResponse,
  SubscriptionResponse,
  GenerateReportRequest
} from '../services/api';

interface Report extends ReportResponse {
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
    includeMetadata?: boolean;
  };
}

interface Subscription extends SubscriptionResponse {
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
  };
}

const reportTypes = [
  { value: 'detection', label: 'Track Detections' },
  { value: 'analytics', label: 'Analytics Overview' },
  { value: 'summary', label: 'Summary Report' },
  { value: 'artist', label: 'Artist Details' },
  { value: 'track', label: 'Track Analysis' },
  { value: 'station', label: 'Station Statistics' },
  { value: 'label', label: 'Label Report' }
];

const reportFormats = [
  { value: 'csv', label: 'CSV' },
  { value: 'xlsx', label: 'Excel' },
  { value: 'json', label: 'JSON' }
];

const frequencies = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' }
];

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [selectedFilters, setSelectedFilters] = useState({
    artists: [],
    stations: [],
    labels: [],
    minConfidence: 80,
    includeMetadata: true
  });
  const [selectedDates, setSelectedDates] = useState<[Date, Date]>([new Date(), new Date()]);
  const [selectedType, setSelectedType] = useState('detection');
  const [selectedFormat, setSelectedFormat] = useState('csv');
  const [subscriptionForm, setSubscriptionForm] = useState({
    name: '',
    type: 'detection',
    frequency: 'daily',
    recipients: ''
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchData();
  }, []);

  const handleUnauthorized = () => {
    // Clear token and redirect to login
    localStorage.removeItem('token');
    navigate('/login', { state: { from: location.pathname } });
  };

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [reportsData, subscriptionsData] = await Promise.all([
        fetchReports(),
        getReportSubscriptions()
      ]);

      // Set reports and subscriptions, ensuring they are arrays
      setReports(Array.isArray(reportsData) ? reportsData : []);
      setSubscriptions(Array.isArray(subscriptionsData) ? subscriptionsData : []);
    } catch (error: any) {
      console.error('Error fetching data:', error);
      if (error?.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      const errorMessage = error?.response?.data?.detail || 'Failed to fetch data';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        status: 'error',
        duration: 5000,
      });
      // Reset data on error
      setReports([]);
      setSubscriptions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const reportRequest: GenerateReportRequest = {
        type: selectedType,
        format: selectedFormat,
        start_date: selectedDates[0].toISOString(),
        end_date: selectedDates[1].toISOString(),
        filters: selectedFilters,
        include_graphs: true,
        language: 'fr' // or get from user preferences
      };

      const data = await generateReport(reportRequest);

      toast({
        title: 'Report generation started',
        status: 'success',
        duration: 3000,
      });

      // Refresh reports list
      fetchData();
    } catch (error: any) {
      console.error('Error generating report:', error);
      if (error?.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      toast({
        title: 'Error',
        description: 'Failed to generate report',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleDownload = async (report: Report) => {
    try {
      const blob = await downloadReport(report.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}-${new Date(report.generatedAt).toISOString()}.${report.format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      console.error('Error downloading report:', error);
      if (error?.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      toast({
        title: 'Error',
        description: 'Failed to download report',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleToggleSubscription = async (id: string, active: boolean) => {
    try {
      await updateSubscription(id, { active });
      setSubscriptions(subscriptions.map(sub =>
        sub.id === id ? { ...sub, active } : sub
      ));
      toast({
        title: `Subscription ${active ? 'activated' : 'deactivated'}`,
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error toggling subscription:', error);
      toast({
        title: 'Error',
        description: 'Failed to update subscription',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleDeleteSubscription = async (id: string) => {
    try {
      await deleteSubscription(id);
      setSubscriptions(subscriptions.filter(sub => sub.id !== id));
      toast({
        title: 'Subscription deleted',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error deleting subscription:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete subscription',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await createSubscription({
        name: subscriptionForm.name,
        type: subscriptionForm.type,
        frequency: subscriptionForm.frequency,
        recipients: subscriptionForm.recipients.split(',').map(r => r.trim()),
        filters: selectedFilters
      });

      setSubscriptions([...subscriptions, {
        ...data,
        active: true,
        nextDelivery: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // Tomorrow
      }]);

      setShowSubscriptionModal(false);
      toast({
        title: 'Subscription created',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error creating subscription:', error);
      toast({
        title: 'Error',
        description: 'Failed to create subscription',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'pending':
        return 'yellow';
      case 'generating':
        return 'blue';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <Container maxW="container.xl" py={5}>
      <VStack spacing={5} align="stretch">
        {isLoading ? (
          <Progress size="xs" isIndeterminate />
        ) : error ? (
          <Text color="red.500" textAlign="center">{error}</Text>
        ) : (
          <>
            <HStack justify="space-between">
              <Heading size="lg">Reports & Subscriptions</Heading>
              <Button
                colorScheme="green"
                onClick={() => setShowSubscriptionModal(true)}
                leftIcon={<Icon as={FaPlus} />}
              >
                Create Subscription
              </Button>
            </HStack>

            <Card>
              <CardBody>
                <form onSubmit={handleGenerateReport}>
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                    <FormControl isRequired>
                      <FormLabel htmlFor="reportType">Report Type</FormLabel>
                      <Select
                        id="reportType"
                        value={selectedType}
                        onChange={(e) => setSelectedType(e.target.value)}
                        aria-label="Select report type"
                        title="Report type selector"
                      >
                        {reportTypes.map(type => (
                          <option key={type.value} value={type.value}>{type.label}</option>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel htmlFor="reportFormat">Format</FormLabel>
                      <Select
                        id="reportFormat"
                        value={selectedFormat}
                        onChange={(e) => setSelectedFormat(e.target.value)}
                        aria-label="Select report format"
                        title="Report format selector"
                      >
                        {reportFormats.map(format => (
                          <option key={format.value} value={format.value}>{format.label}</option>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel>Date Range</FormLabel>
                      <Input
                        id="startDate"
                        type="date"
                        value={selectedDates[0].toISOString().split('T')[0]}
                        onChange={(e) => setSelectedDates([new Date(e.target.value), selectedDates[1]])}
                      />
                      <Input
                        id="endDate"
                        type="date"
                        value={selectedDates[1].toISOString().split('T')[0]}
                        onChange={(e) => setSelectedDates([selectedDates[0], new Date(e.target.value)])}
                        mt={2}
                      />
                    </FormControl>
                  </SimpleGrid>

                  <Button
                    mt={6}
                    colorScheme="blue"
                    type="submit"
                    width="full"
                  >
                    Generate Report
                  </Button>
                </form>
              </CardBody>
            </Card>

            <Tabs>
              <TabList>
                <Tab>Generated Reports</Tab>
                <Tab>Subscriptions</Tab>
              </TabList>

              <TabPanels>
                <TabPanel>
                  <VStack spacing={4} align="stretch">
                    {Array.isArray(reports) && reports.length > 0 ? (
                      reports.map((report) => (
                        <Card key={report.id}>
                          <CardBody>
                            <HStack justify="space-between">
                              <VStack align="start" spacing={1}>
                                <Text fontWeight="bold">{report.title}</Text>
                                <Text fontSize="sm" color={textColor}>
                                  Generated: {new Date(report.generatedAt).toLocaleString()}
                                </Text>
                              </VStack>
                              <HStack>
                                <Badge colorScheme={getStatusColor(report.status)}>
                                  {report.status}
                                </Badge>
                                {report.status === 'generating' && report.progress && (
                                  <Progress
                                    value={report.progress * 100}
                                    size="sm"
                                    width="100px"
                                  />
                                )}
                                {report.status === 'completed' && report.downloadUrl && (
                                  <Button
                                    size="sm"
                                    onClick={() => handleDownload(report)}
                                    leftIcon={<Icon as={FaDownload} />}
                                  >
                                    Download
                                  </Button>
                                )}
                              </HStack>
                            </HStack>
                          </CardBody>
                        </Card>
                      ))
                    ) : (
                      <Text textAlign="center" color={textColor}>
                        No reports available
                      </Text>
                    )}
                  </VStack>
                </TabPanel>

                <TabPanel>
                  <VStack spacing={4} align="stretch">
                    {Array.isArray(subscriptions) && subscriptions.length > 0 ? (
                      subscriptions.map((subscription) => (
                        <Card key={subscription.id}>
                          <CardBody>
                            <HStack justify="space-between">
                              <VStack align="start" spacing={1}>
                                <Text fontWeight="bold">{subscription.name}</Text>
                                <Text fontSize="sm" color={textColor}>
                                  {subscription.type} report - {subscription.frequency}
                                </Text>
                                <Text fontSize="sm" color={textColor}>
                                  Next delivery: {new Date(subscription.nextDelivery).toLocaleString()}
                                </Text>
                              </VStack>
                              <HStack>
                                <Switch
                                  isChecked={subscription.active}
                                  onChange={(e) => handleToggleSubscription(subscription.id, e.target.checked)}
                                />
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  colorScheme="red"
                                  onClick={() => handleDeleteSubscription(subscription.id)}
                                  leftIcon={<Icon as={FaTrash} />}
                                >
                                  Delete
                                </Button>
                              </HStack>
                            </HStack>
                          </CardBody>
                        </Card>
                      ))
                    ) : (
                      <Text textAlign="center" color={textColor}>
                        No active subscriptions
                      </Text>
                    )}
                  </VStack>
                </TabPanel>
              </TabPanels>
            </Tabs>

            <Modal
              isOpen={showSubscriptionModal}
              onClose={() => setShowSubscriptionModal(false)}
            >
              <ModalOverlay />
              <ModalContent>
                <ModalHeader>Create Subscription</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                  <VStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel htmlFor="subscriptionName">Subscription Name</FormLabel>
                      <Input
                        id="subscriptionName"
                        value={subscriptionForm.name}
                        onChange={(e) => setSubscriptionForm({...subscriptionForm, name: e.target.value})}
                        placeholder="Daily Detection Report"
                      />
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel htmlFor="subscriptionType">Report Type</FormLabel>
                      <Select
                        id="subscriptionType"
                        value={subscriptionForm.type}
                        onChange={(e) => setSubscriptionForm({...subscriptionForm, type: e.target.value})}
                        aria-label="Select subscription report type"
                        title="Subscription report type selector"
                      >
                        {reportTypes.map(type => (
                          <option key={type.value} value={type.value}>{type.label}</option>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel htmlFor="subscriptionFrequency">Frequency</FormLabel>
                      <Select
                        id="subscriptionFrequency"
                        value={subscriptionForm.frequency}
                        onChange={(e) => setSubscriptionForm({...subscriptionForm, frequency: e.target.value})}
                        aria-label="Select subscription frequency"
                        title="Subscription frequency selector"
                      >
                        {frequencies.map(freq => (
                          <option key={freq.value} value={freq.value}>{freq.label}</option>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel htmlFor="subscriptionRecipients">Recipients</FormLabel>
                      <Input
                        id="subscriptionRecipients"
                        type="email"
                        value={subscriptionForm.recipients}
                        onChange={(e) => setSubscriptionForm({...subscriptionForm, recipients: e.target.value})}
                        placeholder="Enter email addresses (comma-separated)"
                      />
                    </FormControl>
                  </VStack>
                </ModalBody>

                <ModalFooter>
                  <Button variant="ghost" mr={3} onClick={() => setShowSubscriptionModal(false)}>
                    Cancel
                  </Button>
                  <Button colorScheme="blue" onClick={handleCreateSubscription}>
                    Create
                  </Button>
                </ModalFooter>
              </ModalContent>
            </Modal>
          </>
        )}
      </VStack>
    </Container>
  );
};

export default Reports;
