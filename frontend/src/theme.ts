import { extendTheme, type ThemeConfig, type ThemeComponents } from '@chakra-ui/react'
import { mode, type StyleFunctionProps } from '@chakra-ui/theme-tools'

const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: true,
}

const components: ThemeComponents = {
  Button: {
    defaultProps: {
      colorScheme: 'brand',
    },
    variants: {
      solid: (props: StyleFunctionProps) => ({
        bg: mode('brand.500', 'brand.200')(props),
        color: mode('white', 'gray.800')(props),
        _hover: {
          bg: mode('brand.600', 'brand.300')(props),
        },
      }),
      outline: {
        borderWidth: '2px',
      },
    },
  },
  Select: {
    baseStyle: {
      field: {
        _focus: {
          borderColor: 'brand.500',
          boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)',
        },
      },
    },
  },
  Input: {
    defaultProps: {
      focusBorderColor: 'brand.500',
    },
  },
  Table: {
    variants: {
      simple: {
        th: {
          borderColor: mode('gray.200', 'gray.700'),
          color: mode('gray.600', 'gray.400'),
        },
        td: {
          borderColor: mode('gray.200', 'gray.700'),
        },
      },
    },
  },
}

const semanticTokens = {
  colors: {
    'chakra-body-bg': { _light: 'gray.50', _dark: 'gray.800' },
    'chakra-body-text': { _light: 'gray.800', _dark: 'whiteAlpha.900' },
    'chakra-border-color': { _light: 'gray.200', _dark: 'gray.700' },
    'chakra-placeholder-color': { _light: 'gray.500', _dark: 'gray.400' },
  },
}

const theme = extendTheme({
  config,
  colors: {
    brand: {
      50: '#f5fee5',
      100: '#e1fbb2',
      200: '#cdf781',
      300: '#b8ee56',
      400: '#a2e032',
      500: '#8ac919', // Primary brand color
      600: '#71ab09',
      700: '#578602',
      800: '#3c5e00',
      900: '#203300',
    },
    accent: {
      yellow: '#FCD116', // Senegalese flag yellow
      red: '#E31B23',    // Senegalese flag red
      green: '#00853F',  // SODAV primary green
    },
  },
  fonts: {
    heading: 'Montserrat, system-ui, sans-serif',
    body: 'Inter, system-ui, sans-serif',
  },
  components,
  semanticTokens,
  styles: {
    global: (props: StyleFunctionProps) => ({
      body: {
        bg: mode('gray.50', 'gray.800')(props),
        color: mode('gray.800', 'whiteAlpha.900')(props),
      },
      '*::placeholder': {
        color: mode('gray.500', 'gray.400')(props),
      },
      '*, *::before, *::after': {
        borderColor: mode('gray.200', 'gray.700')(props),
      },
    }),
  },
})

export default theme 