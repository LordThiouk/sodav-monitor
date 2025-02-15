import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  colors: {
    brand: {
      green: '#00853F',  // Senegalese flag green
      yellow: '#FCD116',  // Senegalese flag yellow
      red: '#E31B23',    // Senegalese flag red
    },
  },
  components: {
    Button: {
      variants: {
        solid: {
          bg: 'brand.green',
          color: 'white',
          _hover: {
            bg: 'brand.green',
            opacity: 0.9,
          },
        },
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'lg',
          boxShadow: 'sm',
        },
      },
    },
  },
  styles: {
    global: {
      body: {
        bg: 'gray.50',
      },
    },
  },
});

export default theme;
