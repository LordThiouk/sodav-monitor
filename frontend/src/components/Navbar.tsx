import React from 'react';
import {
  Box,
  Flex,
  IconButton,
  Button,
  HStack,
  useMediaQuery,
  Drawer,
  DrawerBody,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  List,
  ListItem,
  Icon,
  Text,
  useColorModeValue,
  useDisclosure,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Avatar
} from '@chakra-ui/react';
import { HamburgerIcon, CloseIcon, ChevronDownIcon } from '@chakra-ui/icons';
import { FaBroadcastTower, FaChartBar, FaFileDownload, FaMusic, FaChartLine, FaSignInAlt, FaSignOutAlt, FaUserPlus } from 'react-icons/fa';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { isAuthenticated, getUser, removeToken } from '../services/auth';

export default function Navbar() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useMediaQuery("(max-width: 48em)")[0];
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const authenticated = isAuthenticated();
  const user = getUser();

  const navItems = [
    { to: '/', label: 'Live Monitor', icon: FaMusic },
    { to: '/channels', label: 'Channels', icon: FaBroadcastTower },
    { to: '/analytics', label: 'Analytics', icon: FaChartBar },
    { to: '/monitoring', label: 'Monitoring', icon: FaChartLine },
    { to: '/reports', label: 'Reports', icon: FaFileDownload }
  ];

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  return (
    <Box>
      <Box
        as="nav"
        position="fixed"
        w="100%"
        bg={bgColor}
        borderBottom="1px"
        borderColor={borderColor}
        zIndex="sticky"
      >
        <Flex
          h="16"
          alignItems="center"
          justifyContent="space-between"
          mx="auto"
          px={4}
          maxW="container.xl"
        >
          {isMobile && (
            <IconButton
              aria-label="Open menu"
              icon={isOpen ? <CloseIcon /> : <HamburgerIcon />}
              onClick={isOpen ? onClose : onOpen}
              variant="ghost"
            />
          )}

          <Flex align="center">
            <Icon
              as={FaMusic}
              w={5}
              h={5}
              color="brand.500"
            />
            <Text
              fontSize="xl"
              fontWeight="bold"
              bgGradient="linear(to-r, brand.500, brand.600)"
              bgClip="text"
            >
              SODAV Monitor
            </Text>
          </Flex>

          {!isMobile && (
            <>
              {authenticated ? (
                <HStack spacing={4}>
                  {navItems.map((item) => (
                    <Button
                      key={item.to}
                      as={RouterLink}
                      to={item.to}
                      variant={location.pathname === item.to ? 'solid' : 'ghost'}
                      colorScheme="brand"
                      leftIcon={<Icon as={item.icon} />}
                      size="md"
                    >
                      {item.label}
                    </Button>
                  ))}
                </HStack>
              ) : (
                <HStack spacing={4}>
                  <Button
                    as={RouterLink}
                    to="/login"
                    variant="ghost"
                    colorScheme="brand"
                    leftIcon={<Icon as={FaSignInAlt} />}
                    size="md"
                  >
                    Login
                  </Button>
                  <Button
                    as={RouterLink}
                    to="/register"
                    variant="solid"
                    colorScheme="brand"
                    leftIcon={<Icon as={FaUserPlus} />}
                    size="md"
                  >
                    Register
                  </Button>
                </HStack>
              )}
            </>
          )}

          {authenticated && !isMobile && (
            <Menu>
              <MenuButton
                as={Button}
                variant="ghost"
                rightIcon={<ChevronDownIcon />}
                ml={4}
              >
                <HStack>
                  <Avatar size="sm" name={user?.username} />
                  <Text>{user?.username}</Text>
                </HStack>
              </MenuButton>
              <MenuList>
                <MenuItem onClick={handleLogout} icon={<Icon as={FaSignOutAlt} />}>
                  Logout
                </MenuItem>
              </MenuList>
            </Menu>
          )}
        </Flex>
      </Box>

      <Drawer
        isOpen={isOpen && isMobile}
        placement="left"
        onClose={onClose}
      >
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerBody pt={12}>
            {authenticated ? (
              <>
                <Flex align="center" mb={6}>
                  <Avatar size="sm" name={user?.username} mr={2} />
                  <Text fontWeight="bold">{user?.username}</Text>
                </Flex>
                <List spacing={4}>
                  {navItems.map((item) => (
                    <ListItem key={item.to}>
                      <Button
                        as={RouterLink}
                        to={item.to}
                        variant={location.pathname === item.to ? 'solid' : 'ghost'}
                        colorScheme="brand"
                        leftIcon={<Icon as={item.icon} />}
                        w="full"
                        onClick={onClose}
                      >
                        {item.label}
                      </Button>
                    </ListItem>
                  ))}
                  <ListItem>
                    <Button
                      variant="ghost"
                      colorScheme="red"
                      leftIcon={<Icon as={FaSignOutAlt} />}
                      w="full"
                      onClick={() => {
                        handleLogout();
                        onClose();
                      }}
                    >
                      Logout
                    </Button>
                  </ListItem>
                </List>
              </>
            ) : (
              <List spacing={4}>
                <ListItem>
                  <Button
                    as={RouterLink}
                    to="/login"
                    variant="ghost"
                    colorScheme="brand"
                    leftIcon={<Icon as={FaSignInAlt} />}
                    w="full"
                    onClick={onClose}
                  >
                    Login
                  </Button>
                </ListItem>
                <ListItem>
                  <Button
                    as={RouterLink}
                    to="/register"
                    variant="solid"
                    colorScheme="brand"
                    leftIcon={<Icon as={FaUserPlus} />}
                    w="full"
                    onClick={onClose}
                  >
                    Register
                  </Button>
                </ListItem>
              </List>
            )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Add spacing to prevent content from going under fixed navbar */}
      <Box h="16" />
    </Box>
  );
}
