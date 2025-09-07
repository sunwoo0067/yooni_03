import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import PersonalRouter from '@router/PersonalRouter';
import PersonalSidebar from '@components/sidebar/PersonalSidebar';
import PersonalHeader from '@components/header/PersonalHeader';

// 쿼리 클라이언트 생성
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// 테마 생성
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          textTransform: 'none',
        },
      },
    },
  },
});

// 개인 사용자용 메인 애플리케이션
const PersonalApp = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <Box sx={{ display: 'flex', minHeight: '100vh' }}>
            {/* 사이드바 */}
            <PersonalSidebar />
            
            {/* 메인 콘텐츠 */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              {/* 헤더 */}
              <PersonalHeader />
              
              {/* 페이지 콘텐츠 */}
              <Box component="main" sx={{ flex: 1, p: 0, overflow: 'auto' }}>
                <PersonalRouter />
              </Box>
            </Box>
          </Box>
        </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} />
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default PersonalApp;