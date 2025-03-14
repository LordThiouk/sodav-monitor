import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Text,
} from '@chakra-ui/react';
import { fetchStations } from '../services/api';
import { RadioStation } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

interface StreamData {
  station: RadioStation;
  detections: number;
}

const Streams: React.FC = () => {
  const [data, setData] = useState<StreamData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const stations = await fetchStations();

        const streamData = stations.map(station => ({
          station,
          detections: station.last_detection?.total_tracks || 0
        }));

        setData(streamData);
        setError(null);
      } catch (err) {
        console.error('Error loading stream data:', err);
        setError('Failed to load stream data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <Text color="red.500">{error}</Text>;

  return (
    <Container maxW="container.xl">
      {/* Your stream display logic here */}
    </Container>
  );
};

export default Streams;
