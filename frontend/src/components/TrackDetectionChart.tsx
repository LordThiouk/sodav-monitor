import React, { useMemo } from 'react';
import { Box, Heading, useColorModeValue } from '@chakra-ui/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface ChartData {
  timestamp: number;
  confidence: number;
}

interface TrackDetectionChartProps {
  data: ChartData[];
  height?: string | number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: ChartData;
  }>;
  label?: string | number;
}

const TrackDetectionChart: React.FC<TrackDetectionChartProps> = ({ 
  data,
  height = "400px"
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const tooltipBg = useColorModeValue('white', 'gray.700');
  const tooltipColor = useColorModeValue('gray.800', 'white');

  const formatTimestamp = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  const formatTooltipLabel = (label: string | number): string => {
    if (typeof label === 'number') {
      return formatTimestamp(label);
    }
    return label;
  };

  const formatTooltipValue = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const memoizedData = useMemo(() => data, [data]);

  const CustomTooltip = ({ 
    active, 
    payload, 
    label 
  }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
      return (
        <Box
          bg={tooltipBg}
          p={2}
          borderRadius="md"
          boxShadow="md"
          border="1px"
          borderColor={borderColor}
        >
          <Box color={tooltipColor}>
            <Box fontWeight="medium">{formatTooltipLabel(label || '')}</Box>
            <Box>
              Confidence: {formatTooltipValue(payload[0].value)}
            </Box>
          </Box>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box
      p={4}
      bg={bgColor}
      borderRadius="lg"
      borderWidth="1px"
      borderColor={borderColor}
      height={height}
      role="region"
      aria-label="Detection Confidence Chart"
    >
      <Heading size="md" mb={4}>Detection Confidence Over Time</Heading>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart
          data={memoizedData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTimestamp}
          />
          <YAxis
            domain={[0, 100]}
          />
          <Tooltip
            content={CustomTooltip}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="confidence"
            stroke="#8ac919"
            activeDot={{ r: 8 }}
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default React.memo(TrackDetectionChart);
