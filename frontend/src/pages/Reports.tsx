import React from 'react';
import {
  Box,
  VStack,
  Heading,
  Text,
  Select,
  Input,
  Button,
  useColorModeValue,
  Flex,
  useDisclosure,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Switch,
  RadioGroup,
  Radio,
  Stack,
  Badge
} from '@chakra-ui/react';
import { FaDownload, FaFilter } from 'react-icons/fa';

// Simplify types and interfaces
type ReportType = 'plays' | 'artists' | 'tracks' | 'channels';
type Frequency = 'daily' | 'weekly' | 'monthly';

interface FilterState {
  startDate: string;
  endDate: string;
  channel: string;
  artist: string;
  track: string;
  isrc: string;
  reportType: ReportType;
}

interface SubscriptionFilters {
  channel: string;
  artist: string;
  track: string;
  isrc: string;
}

interface SubscriptionState {
  id: string;
  email: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  time: string;
  reportType: ReportType;
  filters: SubscriptionFilters;
  active: boolean;
  lastDelivery: string;
  nextDelivery: string;
}

interface ReportTypeOption {
  value: ReportType;
  label: string;
}

interface Channel {
  id: string;
  name: string;
}

interface ReportFiltersProps {
  filters: FilterState;
  handleSelectChange: (e: React.ChangeEvent<HTMLSelectElement>, field: keyof FilterState) => void;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>, field: keyof FilterState) => void;
  handleFilterChange: (field: keyof FilterState, value: string) => void;
  reportTypes: ReportTypeOption[];
  channels: Channel[];
}

// Separate components for form elements
const FormSelect: React.FC<{
  id: string;
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
}> = ({ id, label, value, onChange, options, placeholder }) => (
  <Select
    id={id}
    value={value}
    onChange={onChange}
    aria-label={label}
    placeholder={placeholder}
  >
    {options.map(option => (
      <option key={option.value} value={option.value}>
        {option.label}
      </option>
    ))}
  </Select>
);

const FormInput: React.FC<{
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
}> = ({ id, label, type = 'text', value, onChange, placeholder }) => (
  <Input
    id={id}
    type={type}
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    aria-label={label}
  />
);

const ReportFilters: React.FC<ReportFiltersProps> = ({ 
  filters, 
  handleSelectChange, 
  handleInputChange, 
  handleFilterChange,
  reportTypes,
  channels 
}) => {
  return (
    <VStack spacing={4} align="stretch">
      <FormSelect
        id="reportType"
        label="Report Type"
        value={filters.reportType}
        onChange={(e) => handleSelectChange(e, 'reportType')}
        options={reportTypes.map(opt => ({ value: opt.value, label: opt.label }))}
      />

      <FormInput
        id="startDate"
        label="Start Date"
        type="date"
        value={filters.startDate}
        onChange={(e) => handleInputChange(e, 'startDate')}
      />

      <FormInput
        id="endDate"
        label="End Date"
        type="date"
        value={filters.endDate}
        onChange={(e) => handleInputChange(e, 'endDate')}
      />

      <FormSelect
        id="channel"
        label="Channel"
        value={filters.channel}
        onChange={(e) => handleSelectChange(e, 'channel')}
        options={channels.map(ch => ({ value: ch.id, label: ch.name }))}
        placeholder="All Channels"
      />

      <FormInput
        id="artist"
        label="Artist"
        value={filters.artist}
        onChange={(e) => handleFilterChange('artist', e.target.value)}
        placeholder="Search by artist"
      />

      <FormInput
        id="track"
        label="Track"
        value={filters.track}
        onChange={(e) => handleFilterChange('track', e.target.value)}
        placeholder="Search by track"
      />

      <FormInput
        id="isrc"
        label="ISRC"
        value={filters.isrc}
        onChange={(e) => handleFilterChange('isrc', e.target.value)}
        placeholder="Search by ISRC"
      />
    </VStack>
  );
};

const Reports = (): React.ReactElement => {
  const [filters, setFilters] = React.useState<FilterState>({
    startDate: '',
    endDate: '',
    channel: '',
    artist: '',
    track: '',
    isrc: '',
    reportType: 'plays',
  });

  const [subscriptions, setSubscriptions] = React.useState<SubscriptionState[]>([
    {
      id: '1',
      email: 'test@example.com',
      frequency: 'daily',
      time: '09:00',
      reportType: 'plays',
      filters: {
        channel: '1',
        artist: '',
        track: '',
        isrc: '',
      },
      active: true,
      lastDelivery: '2024-02-06 09:00',
      nextDelivery: '2024-02-07 09:00',
    },
    {
      id: '2',
      email: 'reports@example.com',
      frequency: 'weekly',
      time: '10:00',
      reportType: 'artists',
      filters: {
        channel: '',
        artist: '',
        track: '',
        isrc: '',
      },
      active: false,
      lastDelivery: '2024-01-30 10:00',
      nextDelivery: '2024-02-13 10:00',
    },
  ]);

  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  const reportTypeOptions: ReportTypeOption[] = [
    { value: 'plays', label: 'Plays Report' },
    { value: 'artists', label: 'Artists Report' },
    { value: 'tracks', label: 'Tracks Report' },
    { value: 'channels', label: 'Channels Report' },
  ];

  const channelOptions: Channel[] = [
    { id: '1', name: 'Radio Future Media 94.0 FM' },
    { id: '2', name: 'Sud FM' },
  ];

  const sampleData = [
    {
      date: '2024-02-06',
      channel: 'Radio Future Media',
      track: 'Sample Track 1',
      artist: 'Sample Artist 1',
      isrc: 'USABC1234567',
      duration: '03:45',
      status: 'Verified'
    },
    {
      date: '2024-02-06',
      channel: 'Sud FM',
      track: 'Sample Track 2',
      artist: 'Sample Artist 2',
      isrc: 'USABC1234568',
      duration: '04:12',
      status: 'Verified'
    },
  ];

  const handleFilterChange = (field: keyof FilterState, value: string): void => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>, field: keyof FilterState): void => {
    handleFilterChange(field, e.target.value);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>, field: keyof FilterState): void => {
    handleFilterChange(field, e.target.value);
  };

  const generateCSV = (data: typeof sampleData): string => {
    const headers = {
      plays: ['Date', 'Channel', 'Track', 'Artist', 'ISRC', 'Duration', 'Status'],
      artists: ['Artist', 'Total Plays', 'Total Duration', 'Most Played Track'],
      tracks: ['Track', 'Artist', 'ISRC', 'Total Plays', 'Total Duration'],
      channels: ['Channel', 'Country', 'Total Plays', 'Total Duration', 'Unique Tracks']
    };

    const selectedHeaders = headers[filters.reportType as keyof typeof headers];
    let csv = selectedHeaders.join(',') + '\n';

    data.forEach(row => {
      const values = selectedHeaders.map(header => {
        const value = row[header.toLowerCase() as keyof typeof row] || '';
        return `"${value.toString().replace(/"/g, '""')}"`;
      });
      csv += values.join(',') + '\n';
    });

    return csv;
  };

  const handleDownload = (): void => {
    try {
      const csv = generateCSV(sampleData);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const date = new Date().toISOString().split('T')[0];
      const filename = `sodav_${filters.reportType}_report_${date}.csv`;
      
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast({
        title: 'Report Downloaded',
        description: `Your ${filters.reportType} report has been downloaded successfully.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error generating report:', error);
      toast({
        title: 'Download Failed',
        description: 'There was an error generating your report. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleClearFilters = (): void => {
    setFilters({
      startDate: '',
      endDate: '',
      channel: '',
      artist: '',
      track: '',
      isrc: '',
      reportType: 'plays',
    });
  };

  const handleToggleSubscription = (id: string): void => {
    setSubscriptions((prev: SubscriptionState[]) => 
      prev.map((sub: SubscriptionState) => {
        if (sub.id === id) {
          const newStatus = !sub.active;
          toast({
            title: `Subscription ${newStatus ? 'Activated' : 'Deactivated'}`,
            description: newStatus 
              ? `Reports will resume delivery to ${sub.email}`
              : `Reports to ${sub.email} have been paused`,
            status: newStatus ? 'success' : 'info',
            duration: 5000,
            isClosable: true,
          });
          return { ...sub, active: newStatus };
        }
        return sub;
      })
    );
  };

  const handleSubscriptionChange = (field: keyof SubscriptionState, value: string | boolean): void => {
    setSubscriptions(prev => prev.map(sub => sub.id === '1' ? { ...sub, [field]: value } : sub));
  };

  const handleSubscriptionFilterChange = (field: keyof SubscriptionFilters, value: string): void => {
    setSubscriptions(prev => prev.map(sub => sub.id === '1' ? { ...sub, filters: { ...sub.filters, [field]: value } } : sub));
  };

  // Update event handlers with proper types
  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionChange('email', e.target.value);
  };

  const handleReportTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    handleSubscriptionChange('reportType', e.target.value as ReportType);
  };

  const handleFrequencyChange = (value: string) => {
    handleSubscriptionChange('frequency', value as Frequency);
  };

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionChange('time', e.target.value);
  };

  const handleChannelFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    handleSubscriptionFilterChange('channel', e.target.value);
  };

  const handleArtistFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionFilterChange('artist', e.target.value);
  };

  const handleTrackFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionFilterChange('track', e.target.value);
  };

  const handleIsrcFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionFilterChange('isrc', e.target.value);
  };

  const handleActiveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSubscriptionChange('active', e.target.checked);
  };

  const handleSubscribe = (): void => {
    toast({
      title: 'Subscription Created',
      description: `You will receive ${subscriptions[0].frequency} reports at ${subscriptions[0].time} to ${subscriptions[0].email}`,
      status: 'success',
      duration: 5000,
      isClosable: true,
    });
    onClose();
  };

  return (
    <Box maxW="container.xl">
      <VStack spacing={8} align="stretch">
        <Box>
          <Heading size="lg">Reports</Heading>
          <Text color={textColor} mt={2}>
            Generate and download custom reports
          </Text>
        </Box>

        <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
          <VStack spacing={6} align="stretch">
            <Flex justify="space-between" align="center">
              <Heading size="md">Report Filters</Heading>
              <Button
                leftIcon={<FaFilter />}
                colorScheme="blue"
                variant="outline"
                onClick={onOpen}
                size="sm"
              >
                Schedule Reports
              </Button>
            </Flex>

            <ReportFilters 
              filters={filters}
              handleSelectChange={handleSelectChange}
              handleInputChange={handleInputChange}
              handleFilterChange={handleFilterChange}
              reportTypes={reportTypeOptions}
              channels={channelOptions}
            />

            <Flex gap={4} mt={4}>
              <Button
                leftIcon={<FaDownload />}
                colorScheme="green"
                onClick={handleDownload}
                isDisabled={!filters.startDate || !filters.endDate}
              >
                Download Report
              </Button>
              <Button
                leftIcon={<FaFilter />}
                variant="outline"
                onClick={handleClearFilters}
              >
                Clear Filters
              </Button>
            </Flex>
          </VStack>
        </Box>

        {/* Active Subscriptions Section */}
        <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
          <VStack spacing={4} align="stretch">
            <Heading size="md">Active Subscriptions</Heading>
            <Box overflowX="auto">
              <Table>
                <Thead>
                  <Tr>
                    <Th>Email</Th>
                    <Th>Report Type</Th>
                    <Th>Frequency</Th>
                    <Th>Time</Th>
                    <Th>Last Delivery</Th>
                    <Th>Next Delivery</Th>
                    <Th>Status</Th>
                    <Th>Action</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {subscriptions.map((sub) => (
                    <Tr key={sub.id}>
                      <Td>{sub.email}</Td>
                      <Td>{reportTypeOptions.find(t => t.value === sub.reportType)?.label}</Td>
                      <Td style={{ textTransform: 'capitalize' }}>{sub.frequency}</Td>
                      <Td>{sub.time}</Td>
                      <Td>{sub.lastDelivery}</Td>
                      <Td>{sub.nextDelivery}</Td>
                      <Td>
                        <Badge 
                          colorScheme={sub.active ? 'green' : 'gray'}
                        >
                          {sub.active ? 'Active' : 'Paused'}
                        </Badge>
                      </Td>
                      <Td>
                        <Switch
                          isChecked={sub.active}
                          onChange={() => handleToggleSubscription(sub.id)}
                        />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </VStack>
        </Box>

        {/* Preview Section */}
        <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
          <VStack spacing={4} align="stretch">
            <Heading size="md">Report Preview</Heading>
            <Box overflowX="auto">
              <Table>
                <Thead>
                  <Tr>
                    <Th>Date</Th>
                    <Th>Channel</Th>
                    <Th>Track</Th>
                    <Th>Artist</Th>
                    <Th>ISRC</Th>
                    <Th>Duration</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {sampleData.map((row, index) => (
                    <Tr key={index}>
                      <Td>{row.date}</Td>
                      <Td>{row.channel}</Td>
                      <Td>{row.track}</Td>
                      <Td>{row.artist}</Td>
                      <Td>{row.isrc}</Td>
                      <Td>{row.duration}</Td>
                      <Td>
                        <Badge 
                          colorScheme="green"
                        >
                          {row.status}
                        </Badge>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </VStack>
        </Box>

        {/* Subscription Modal */}
        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Schedule Report Delivery</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <FormControl>
                <FormLabel>Email Address</FormLabel>
                <Input
                  type="email"
                  value={subscriptions[0].email}
                  onChange={handleEmailChange}
                  placeholder="Enter your email"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Report Type</FormLabel>
                <Select
                  value={subscriptions[0].reportType}
                  onChange={handleReportTypeChange}
                >
                  {reportTypeOptions.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Frequency</FormLabel>
                <RadioGroup
                  value={subscriptions[0].frequency}
                  onChange={handleFrequencyChange}
                >
                  <Stack direction="row">
                    <Radio value="daily">Daily</Radio>
                    <Radio value="weekly">Weekly</Radio>
                    <Radio value="monthly">Monthly</Radio>
                  </Stack>
                </RadioGroup>
              </FormControl>

              <FormControl>
                <FormLabel>Delivery Time</FormLabel>
                <Input
                  type="time"
                  value={subscriptions[0].time}
                  onChange={handleTimeChange}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Filters</FormLabel>

                <FormControl>
                  <FormLabel>Channel</FormLabel>
                  <Select
                    value={subscriptions[0].filters.channel}
                    onChange={handleChannelFilterChange}
                  >
                    {channelOptions.map(channel => (
                      <option key={channel.id} value={channel.id}>
                        {channel.name}
                      </option>
                    ))}
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Artist</FormLabel>
                  <Input
                    placeholder="Filter by artist"
                    value={subscriptions[0].filters.artist}
                    onChange={handleArtistFilterChange}
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Track</FormLabel>
                  <Input
                    placeholder="Filter by track"
                    value={subscriptions[0].filters.track}
                    onChange={handleTrackFilterChange}
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>ISRC</FormLabel>
                  <Input
                    placeholder="Filter by ISRC"
                    value={subscriptions[0].filters.isrc}
                    onChange={handleIsrcFilterChange}
                  />
                </FormControl>
              </FormControl>

              <FormControl>
                <FormLabel>Status</FormLabel>
                <Switch
                  isChecked={subscriptions[0].active}
                  onChange={handleActiveChange}
                />
              </FormControl>

              <Button
                onClick={handleSubscribe}
                disabled={!subscriptions[0].email || !subscriptions[0].time}
              >
                Subscribe to Reports
              </Button>
            </ModalBody>
          </ModalContent>
        </Modal>
      </VStack>
    </Box>
  );
};

export default Reports;
