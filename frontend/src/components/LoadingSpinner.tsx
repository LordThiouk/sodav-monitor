import React from 'react';
import { Center, Spinner, Text, VStack } from '@chakra-ui/react';

interface LoadingSpinnerProps {
  message?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = 'Loading...' }) => {
  return (
    <Center h="200px">
      <VStack spacing={4}>
        <Spinner
          thickness="4px"
          speed="0.65s"
          emptyColor="gray.200"
          color="brand.green"
          size="xl"
        />
        <Text color="gray.500">{message}</Text>
      </VStack>
    </Center>
  );
};

export default LoadingSpinner;
