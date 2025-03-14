import React, { useState } from 'react';
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Heading,
  Input,
  VStack,
  useToast,
  Text,
  useColorModeValue,
  Link,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch('/api/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        toast({
          title: 'Reset instructions sent',
          description: 'Please check your email for password reset instructions.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        // For demo purposes only - in production, token should be sent via email
        setResetToken(data.token);
      } else {
        throw new Error(data.detail || 'Failed to send reset instructions');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'An error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxW="container.sm" py={10}>
      <Box
        p={8}
        bg={bgColor}
        borderRadius="lg"
        boxShadow="lg"
        border="1px"
        borderColor={borderColor}
      >
        <VStack spacing={6}>
          <Heading size="lg">Forgot Password</Heading>
          <Text color="gray.600">
            Enter your email address and we'll send you instructions to reset your password.
          </Text>

          <form onSubmit={handleSubmit} style={{ width: '100%' }}>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                />
              </FormControl>

              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                width="100%"
                isLoading={isLoading}
                loadingText="Sending..."
              >
                Send Reset Instructions
              </Button>

              {resetToken && (
                <Alert status="info">
                  <AlertIcon />
                  <Text>
                    Demo mode: Use this link to reset your password:{' '}
                    <Link as={RouterLink} to={`/reset-password?token=${resetToken}`} color="blue.500">
                      Reset Password
                    </Link>
                  </Text>
                </Alert>
              )}

              <Text textAlign="center">
                Remember your password?{' '}
                <Link as={RouterLink} to="/login" color="blue.500">
                  Login here
                </Link>
              </Text>
            </VStack>
          </form>
        </VStack>
      </Box>
    </Container>
  );
};

export default ForgotPassword;
