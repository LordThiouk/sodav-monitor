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

interface Report {
  id: string;
  title: string;
  type: 'detection' | 'analytics' | 'summary' | 'artist' | 'track' | 'station' | 'label';
  format: 'csv' | 'xlsx' | 'json';
  generatedAt: string;
  status: 'completed' | 'pending' | 'failed' | 'generating';
  progress?: number;
  downloadUrl?: string;
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
    includeMetadata?: boolean;
  };
}

interface Subscription {
  id: string;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  type: 'detection' | 'analytics' | 'summary' | 'artist' | 'track' | 'station' | 'label';
  nextDelivery: string;
  recipients: string[];
  filters?: {
    artists?: string[];
    stations?: string[];
    labels?: string[];
    minConfidence?: number;
  };
  active: boolean;
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

  const toast = useToast();
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const reportsResponse = await fetch('/api/reports');
      if (!reportsResponse.ok) {
        if (reportsResponse.status === 401) {
          // Handle unauthorized
          return;
        }
        throw new Error('Failed to fetch reports');
      }
      const reportsData = await reportsResponse.json();
      console.log('Reports API response:', reportsData);
      // Ensure we're setting an array
      setReports(Array.isArray(reportsData) ? reportsData : reportsData.reports || []);

      const subscriptionsResponse = await fetch('/api/reports/subscriptions');
      if (!subscriptionsResponse.ok) {
        if (subscriptionsResponse.status === 401) {
          // Handle unauthorized
          return;
        }
        throw new Error('Failed to fetch subscriptions');
      }
      const subscriptionsData = await subscriptionsResponse.json();
      console.log('Subscriptions API response:', subscriptionsData);
      // Ensure we're setting an array
      setSubscriptions(Array.isArray(subscriptionsData) ? subscriptionsData : subscriptionsData.subscriptions || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch data',
        status: 'error',
        duration: 5000,
      });
      setReports([]);
      setSubscriptions([]);
    }
  };

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: selectedType,
          format: selectedFormat,
          start_date: selectedDates[0].toISOString(),
          end_date: selectedDates[1].toISOString(),
          filters: selectedFilters
        }),
      });

      const data = await response.json();
      if (response.ok) {
        toast({
          title: 'Report generation started',
          status: 'success',
          duration: 3000,
        });
        setReports([
          {
            id: data.id,
            title: `${selectedType} Report`,
            type: selectedType as Report['type'],
            format: selectedFormat as Report['format'],
            status: 'pending',
            generatedAt: new Date().toISOString(),
            filters: selectedFilters
          },
          ...reports
        ]);
      } else {
        toast({
          title: 'Error',
          description: data.message || 'Failed to generate report',
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      console.error('Error generating report:', error);
      toast({
        title: 'Error',
        description: 'Failed to generate report',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleDownload = async (report: Report) => {
    if (!report.downloadUrl) {
      toast({
        title: 'Download not available',
        description: 'Report is not ready for download',
        status: 'warning',
        duration: 5000,
      });
      return;
    }

    try {
      const response = await fetch(report.downloadUrl);
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}-${new Date(report.generatedAt).toISOString()}.${report.format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: 'Download started',
        description: 'Your report will be saved in your downloads folder',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error downloading report:', error);
      toast({
        title: 'Download failed',
        description: 'Unable to download the report',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleToggleSubscription = async (id: string, active: boolean) => {
    try {
      const response = await fetch(`/api/subscriptions/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active }),
      });

      if (response.ok) {
        toast({
          title: `Subscription ${active ? 'activated' : 'deactivated'}`,
          status: 'success',
          duration: 3000,
        });
        setSubscriptions(subscriptions.map(sub => 
          sub.id === id ? { ...sub, active } : sub
        ));
      } else {
        toast({
          title: 'Error',
          description: 'Failed to update subscription',
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      console.error('Error updating subscription:', error);
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
      const response = await fetch(`/api/subscriptions/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast({
          title: 'Subscription deleted',
          status: 'success',
          duration: 3000,
        });
        setSubscriptions(subscriptions.filter(sub => sub.id !== id));
      } else {
        toast({
          title: 'Error',
          description: 'Failed to delete subscription',
          status: 'error',
          duration: 5000,
        });
      }
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
      const recipients = subscriptionForm.recipients.split(',').map(email => email.trim());
      
      const response = await fetch('/api/reports/subscriptions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: subscriptionForm.name,
          type: subscriptionForm.type,
          frequency: subscriptionForm.frequency,
          recipients: recipients
        }),
      });

      const data = await response.json();
      if (response.ok) {
        toast({
          title: 'Subscription created',
          description: 'You will receive reports according to your selected frequency',
          status: 'success',
          duration: 3000,
        });
        setSubscriptions([...subscriptions, data]);
        setShowSubscriptionModal(false);
        setSubscriptionForm({
          name: '',
          type: 'detection',
          frequency: 'daily',
          recipients: ''
        });
      } else {
        throw new Error(data.message || 'Failed to create subscription');
      }
    } catch (error) {
      console.error('Error creating subscription:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to create subscription',
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
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
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
                {reports.map((report) => (
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
                ))}
                {reports.length === 0 && (
                  <Text textAlign="center" color={textColor}>
                    No reports available
                  </Text>
                )}
              </VStack>
            </TabPanel>

            <TabPanel>
              <VStack spacing={4} align="stretch">
                {subscriptions.map((subscription) => (
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
                ))}
                {subscriptions.length === 0 && (
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
      </VStack>
    </Container>
  );
};

export default Reports;
