import { createTheme, alpha } from '@mui/material/styles'
import { koKR } from '@mui/material/locale'

// 공통 설정
const commonSettings = {
  typography: {
    fontFamily: [
      'Pretendard',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: ({ theme }: { theme: any }) => ({
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
          padding: '8px 16px',
        }),
        contained: ({ theme }: { theme: any }) => ({
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
          },
        }),
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.06)',
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0px 4px 16px rgba(0, 0, 0, 0.1)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            transition: 'all 0.2s',
            '&:hover': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderWidth: 2,
              },
            },
            '&.Mui-focused': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderWidth: 2,
              },
            },
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        elevation1: {
          boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRadius: 0,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          borderBottom: '1px solid',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 6,
          fontSize: '0.75rem',
          padding: '6px 12px',
        },
      },
    },
  },
}

// 라이트 테마
export const lightTheme = createTheme(
  {
    palette: {
      mode: 'light',
      primary: {
        main: '#2196F3',
        light: '#64B5F6',
        dark: '#1976D2',
        contrastText: '#FFFFFF',
      },
      secondary: {
        main: '#E91E63',
        light: '#F06292',
        dark: '#C2185B',
        contrastText: '#FFFFFF',
      },
      success: {
        main: '#4CAF50',
        light: '#81C784',
        dark: '#388E3C',
      },
      warning: {
        main: '#FF9800',
        light: '#FFB74D',
        dark: '#F57C00',
      },
      error: {
        main: '#F44336',
        light: '#E57373',
        dark: '#D32F2F',
      },
      info: {
        main: '#00BCD4',
        light: '#4DD0E1',
        dark: '#0097A7',
      },
      background: {
        default: '#F5F7FA',
        paper: '#FFFFFF',
      },
      text: {
        primary: '#1A1A1A',
        secondary: '#666666',
      },
      divider: 'rgba(0, 0, 0, 0.08)',
    },
    ...commonSettings,
    components: {
      ...commonSettings.components,
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: '#FFFFFF',
            borderBottomColor: 'rgba(0, 0, 0, 0.08)',
          },
        },
      },
    },
  },
  koKR
)

// 다크 테마
export const darkTheme = createTheme(
  {
    palette: {
      mode: 'dark',
      primary: {
        main: '#64B5F6',
        light: '#90CAF9',
        dark: '#42A5F5',
        contrastText: '#000000',
      },
      secondary: {
        main: '#F48FB1',
        light: '#F8BBD0',
        dark: '#F06292',
        contrastText: '#000000',
      },
      success: {
        main: '#81C784',
        light: '#A5D6A7',
        dark: '#66BB6A',
      },
      warning: {
        main: '#FFB74D',
        light: '#FFCC80',
        dark: '#FFA726',
      },
      error: {
        main: '#E57373',
        light: '#EF9A9A',
        dark: '#EF5350',
      },
      info: {
        main: '#4DD0E1',
        light: '#80DEEA',
        dark: '#26C6DA',
      },
      background: {
        default: '#0A0E27',
        paper: '#151A3A',
      },
      text: {
        primary: '#FFFFFF',
        secondary: '#B0B0B0',
      },
      divider: 'rgba(255, 255, 255, 0.12)',
    },
    ...commonSettings,
    components: {
      ...commonSettings.components,
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: '#151A3A',
            borderBottomColor: 'rgba(255, 255, 255, 0.12)',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            ...commonSettings.components!.MuiCard!.styleOverrides!.root,
            backgroundColor: '#1A2042',
            boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.3)',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: '0px 4px 16px rgba(0, 0, 0, 0.4)',
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            ...commonSettings.components!.MuiPaper!.styleOverrides!.root,
            backgroundImage: 'none',
          },
          elevation1: {
            boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.3)',
          },
        },
      },
    },
  },
  koKR
)

// 기본 내보내기 (하위 호환성)
const theme = lightTheme
export default theme