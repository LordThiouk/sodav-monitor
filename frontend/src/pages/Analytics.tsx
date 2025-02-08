import React from 'react';
import {
  Box,
  Container,
  Tabs,
  TabList,
  TabPanels,
  TabPanel,
  Tab,
  useColorModeValue,
} from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import AnalyticsOverview from './analytics/AnalyticsOverview';
import AnalyticsTracks from './analytics/AnalyticsTracks';
import AnalyticsArtists from './analytics/AnalyticsArtists';
import AnalyticsLabels from './analytics/AnalyticsLabels';
import AnalyticsChannels from './analytics/AnalyticsChannels';

const Analytics: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Map paths to tab indices
  const pathToIndex: Record<string, number> = {
    '/analytics': 0,
    '/analytics/tracks': 1,
    '/analytics/artists': 2,
    '/analytics/labels': 3,
    '/analytics/channels': 4,
  };

  // Get current tab index from path
  const currentIndex = pathToIndex[location.pathname] || 0;

  // Handle tab change
  const handleTabChange = (index: number) => {
    const paths = [
      '/analytics',
      '/analytics/tracks',
      '/analytics/artists',
      '/analytics/labels',
      '/analytics/channels',
    ];
    navigate(paths[index]);
  };

  return (
    <Container maxW="container.xl" py={4}>
      <Box
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
        overflow="hidden"
      >
        <Tabs
          index={currentIndex}
          onChange={handleTabChange}
          variant="enclosed"
          colorScheme="brand"
          isLazy
        >
          <TabList>
            <Tab>Overview</Tab>
            <Tab>Tracks</Tab>
            <Tab>Artists</Tab>
            <Tab>Labels</Tab>
            <Tab>Channels</Tab>
          </TabList>

          <TabPanels p={4}>
            <TabPanel>
              <AnalyticsOverview />
            </TabPanel>
            <TabPanel>
              <AnalyticsTracks />
            </TabPanel>
            <TabPanel>
              <AnalyticsArtists />
            </TabPanel>
            <TabPanel>
              <AnalyticsLabels />
            </TabPanel>
            <TabPanel>
              <AnalyticsChannels />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Box>
    </Container>
  );
};

export default Analytics; 