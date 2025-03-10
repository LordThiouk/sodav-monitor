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
  InputGroup,
  InputRightElement,
  IconButton,
  Link,
} from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { FaEye, FaEyeSlash } from 'react-icons/fa';
import { setToken, setUser, AuthResponse } from '../services/auth';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data: AuthResponse = await response.json();
      setToken(data.access_token);
      setUser(data.user);
      
      toast({
        title: 'Login successful',
        description: `Welcome back, ${data.user.username}!`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      navigate('/');
    } catch (error) {
      toast({
        title: 'Login failed',
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
          <Heading size="lg">Login</Heading>
          <Text color="gray.600">Please login to access the reports</Text>

          <form onSubmit={handleLogin} style={{ width: '100%' }}>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel>Username</FormLabel>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Password</FormLabel>
                <InputGroup>
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                  />
                  <InputRightElement>
                    <IconButton
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      icon={showPassword ? <FaEyeSlash /> : <FaEye />}
                      variant="ghost"
                      onClick={() => setShowPassword(!showPassword)}
                    />
                  </InputRightElement>
                </InputGroup>
              </FormControl>

              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                width="100%"
                isLoading={isLoading}
                loadingText="Logging in..."
              >
                Login
              </Button>

              <VStack spacing={2}>
                <Text textAlign="center">
                  Don't have an account?{' '}
                  <Link as={RouterLink} to="/register" color="blue.500">
                    Register here
                  </Link>
                </Text>
                <Text textAlign="center">
                  <Link as={RouterLink} to="/forgot-password" color="blue.500">
                    Forgot your password?
                  </Link>
                </Text>
              </VStack>
            </VStack>
          </form>
        </VStack>
      </Box>
    </Container>
  );
};

export default Login; 