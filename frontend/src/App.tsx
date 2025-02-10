import React, { type ErrorInfo } from 'react';
import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import theme from './theme';
import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import LiveMonitor from './components/LiveMonitor';
import Channels from './pages/Channels';
import ChannelDetections from './pages/ChannelDetections';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import PrivateRoute from './components/PrivateRoute';
import AnalyticsOverview from './pages/analytics/AnalyticsOverview';
import AnalyticsArtists from './pages/analytics/AnalyticsArtists';
import AnalyticsTracks from './pages/analytics/AnalyticsTracks';
import AnalyticsLabels from './pages/analytics/AnalyticsLabels';
import AnalyticsChannels from './pages/analytics/AnalyticsChannels';

const App: React.FC = () => {
  const handleError = (error: Error, info: ErrorInfo) => {
    // In a real app, you would log this to an error reporting service
    console.error('Error caught by boundary:', error);
    console.error('Component stack:', info.componentStack);
  };

  return (
    <ChakraProvider theme={theme}>
      <ErrorBoundary onError={handleError}>
        <Router>
          <Navbar />
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/" element={<LiveMonitor />} />
              <Route path="/channels" element={<Channels />} />
              <Route path="/channels/:id/detections" element={<ChannelDetections />} />
              <Route path="/analytics/*" element={<Analytics />} />
              <Route 
                path="/reports" 
                element={
                  <PrivateRoute>
                    <Reports />
                  </PrivateRoute>
                } 
              />
              <Route path="/analytics" element={<AnalyticsOverview />} />
              <Route path="/analytics/artists" element={<AnalyticsArtists />} />
              <Route path="/analytics/tracks" element={<AnalyticsTracks />} />
              <Route path="/analytics/labels" element={<AnalyticsLabels />} />
              <Route path="/analytics/channels" element={<AnalyticsChannels />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ErrorBoundary>
        </Router>
      </ErrorBoundary>
    </ChakraProvider>
  );
};

export default App;
