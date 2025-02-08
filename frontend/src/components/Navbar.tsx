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
  useDisclosure
} from '@chakra-ui/react';
import { HamburgerIcon, CloseIcon } from '@chakra-ui/icons';
import { FaBroadcastTower, FaChartBar, FaFileDownload, FaMusic } from 'react-icons/fa';
import { Link as RouterLink, useLocation } from 'react-router-dom';

export default function Navbar() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const location = useLocation();
  const isMobile = useMediaQuery("(max-width: 48em)")[0];
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const navItems = [
    { to: '/', label: 'Live Monitor', icon: FaMusic },
    { to: '/channels', label: 'Channels', icon: FaBroadcastTower },
    { to: '/analytics', label: 'Analytics', icon: FaChartBar },
    { to: '/reports', label: 'Reports', icon: FaFileDownload }
  ];

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
            </List>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Add spacing to prevent content from going under fixed navbar */}
      <Box h="16" />
    </Box>
  );
}
