import React, { type ErrorInfo } from 'react';
import {
  Box,
  Button,
  Heading,
  Text,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';

interface FallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

const ErrorFallback: React.FC<FallbackProps> = ({ 
  error, 
  resetErrorBoundary 
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box
      p={6}
      bg={bgColor}
      borderRadius="lg"
      borderWidth="1px"
      borderColor={borderColor}
      role="alert"
    >
      <VStack spacing={4} align="start">
        <Heading size="md" color="red.500">
          Something went wrong
        </Heading>
        <Text color="gray.600" _dark={{ color: 'gray.400' }}>
          {error.message}
        </Text>
        <Button
          colorScheme="brand"
          onClick={resetErrorBoundary}
        >
          Try again
        </Button>
      </VStack>
    </Box>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
  onReset?: () => void;
  onError?: (error: Error, info: ErrorInfo) => void;
}

export const ErrorBoundary: React.FC<ErrorBoundaryProps> = ({
  children,
  onReset,
  onError,
}) => {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={onReset}
      onError={onError}
    >
      {children}
    </ReactErrorBoundary>
  );
};

export default ErrorBoundary;
