import React, { Suspense } from 'react'
import { 
  BrowserRouter as Router, 
  Routes, 
  Route, 
  Navigate,
  createBrowserRouter,
  RouterProvider 
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Provider } from 'react-redux'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { LocalizationProvider } from '@mui/x-date-pickers'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import ko from 'date-fns/locale/ko'

// Store
import { store } from '@store/index'
import { setApiStore } from '@services/api'

// Set the store reference for API interceptors
setApiStore(store)

// Layouts
import MainLayout from '@components/layouts/MainLayout'
import AuthLayout from '@components/layouts/AuthLayout'

// Pages - Core pages loaded immediately
import Dashboard from '@pages/Dashboard'
import Products from '@pages/products/Products'
import Orders from '@pages/orders/Orders'

// Auth pages
import Login from '@pages/auth/Login'
const Register = React.lazy(() => import('@pages/auth/Register'))
const ForgotPassword = React.lazy(() => import('@pages/auth/ForgotPassword'))
const ResetPasswordSent = React.lazy(() => import('@pages/auth/ResetPasswordSent'))
const ResetPassword = React.lazy(() => import('@pages/auth/ResetPassword'))
const VerifyEmail = React.lazy(() => import('@pages/auth/VerifyEmail'))

// Pages - Lazy loaded for better performance
const ProductDetail = React.lazy(() => import('@pages/products/ProductDetail'))
const ProductCollector = React.lazy(() => import('@pages/products/ProductCollector'))
const ProductSourcing = React.lazy(() => import('@pages/products/ProductSourcing'))
const WholesalerSync = React.lazy(() => import('@pages/products/WholesalerSync'))
const CollectedProducts = React.lazy(() => import('@pages/products/CollectedProducts'))
const CollectionSchedule = React.lazy(() => import('@pages/products/CollectionSchedule'))
const OrderDetail = React.lazy(() => import('@pages/orders/OrderDetail'))
const PlatformAccounts = React.lazy(() => import('@pages/platforms/PlatformAccounts'))
const Wholesalers = React.lazy(() => import('@pages/wholesalers/Wholesalers'))
const WholesalerAPISettings = React.lazy(() => import('@pages/wholesalers/WholesalerAPISettings'))
const Analytics = React.lazy(() => import('@pages/analytics/Analytics'))
const Marketing = React.lazy(() => import('@pages/marketing/Marketing'))
const Customers = React.lazy(() => import('@pages/customers/Customers'))
const Settings = React.lazy(() => import('@pages/settings/Settings'))
const DevTools = React.lazy(() => import('@pages/DevTools'))

// Research Pages - Lazy loaded
const TrendAnalysis = React.lazy(() => import('@pages/research/TrendAnalysis'))
const CompetitorAnalysis = React.lazy(() => import('@pages/research/CompetitorAnalysis'))

// AI Insights Pages - Lazy loaded
const AIRecommendations = React.lazy(() => import('@pages/ai-insights/AIRecommendations'))
const PriceOptimization = React.lazy(() => import('@pages/ai-insights/PriceOptimization'))
const DemandForecast = React.lazy(() => import('@pages/ai-insights/DemandForecast'))
const AIDashboard = React.lazy(() => import('@pages/ai-insights/AIDashboard'))

// Monitoring Pages - Lazy loaded
const SystemMonitoring = React.lazy(() => import('@pages/monitoring/SystemMonitoring'))

// Error Handling
import ErrorBoundary, { RouteErrorBoundary } from '@components/ui/ErrorBoundary'

// Notification System
import { NotificationProvider, NotificationCenter } from '@components/ui/NotificationSystem'

// WebSocket Service - removed direct import, handled by useWebSocketSync hook

// Customer Support Chat
import CustomerSupportChat from '@components/chat/CustomerSupportChat'

// Auth components
import ProtectedRoute from '@components/auth/ProtectedRoute'
import SessionManager from '@components/auth/SessionManager'

// Hooks
import { useWebSocketSync } from '@hooks/useWebSocketSync'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

// Create MUI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#e91e63',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        },
      },
    },
  },
})

// Auth wrapper component
const AuthWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <>
      <SessionManager />
      {children}
    </>
  )
}

// Loading component for lazy loaded pages
const PageLoader = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '100vh' 
  }}>
    <div>Loading...</div>
  </div>
)

// Suspense wrapper for lazy loaded components
const LazyPage: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <Suspense fallback={<PageLoader />}>
      {children}
    </Suspense>
  )
}

// WebSocketSync wrapper component
const WebSocketSyncWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useWebSocketSync()
  return <>{children}</>
}

function App() {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // 앱 레벨 에러 로깅
        console.error('App-level error:', error, errorInfo)
        // 여기서 실제 에러 리포팅 서비스 (Sentry 등)에 전송 가능
      }}
    >
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <WebSocketSyncWrapper>
            <ThemeProvider theme={theme}>
              <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
                <NotificationProvider>
                <CssBaseline />
                <Router future={{
                  v7_startTransition: true,
                  v7_relativeSplatPath: true
                }}>
                  <Routes>
                    {/* Dev Tools Route */}
                    <Route 
                      path="/devtools" 
                      element={
                        <RouteErrorBoundary>
                          <DevTools />
                        </RouteErrorBoundary>
                      } 
                    />

                    {/* Protected Routes */}
                    <Route
                      element={
                        <ProtectedRoute>
                          <RouteErrorBoundary>
                            <MainLayout />
                          </RouteErrorBoundary>
                        </ProtectedRoute>
                      }
                    >
                      <Route path="/" element={<Navigate to="/dashboard" replace />} />
                      <Route 
                        path="/dashboard" 
                        element={
                          <RouteErrorBoundary>
                            <Dashboard />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products" 
                        element={
                          <RouteErrorBoundary>
                            <Products />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/:id" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <ProductDetail />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/collect" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <ProductCollector />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/sourcing" 
                        element={
                          <RouteErrorBoundary>
                            <ProductSourcing />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/sync" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <WholesalerSync />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/collected" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <CollectedProducts />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/products/collection-schedule" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <CollectionSchedule />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/orders" 
                        element={
                          <RouteErrorBoundary>
                            <Orders />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/orders/:id" 
                        element={
                          <RouteErrorBoundary>
                            <OrderDetail />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/platforms" 
                        element={
                          <RouteErrorBoundary>
                            <PlatformAccounts />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/wholesalers" 
                        element={
                          <RouteErrorBoundary>
                            <Wholesalers />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/wholesalers/api-settings" 
                        element={
                          <RouteErrorBoundary>
                            <LazyPage>
                              <WholesalerAPISettings />
                            </LazyPage>
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/analytics" 
                        element={
                          <RouteErrorBoundary>
                            <Analytics />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/marketing" 
                        element={
                          <RouteErrorBoundary>
                            <Marketing />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/customers" 
                        element={
                          <RouteErrorBoundary>
                            <Customers />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/settings" 
                        element={
                          <RouteErrorBoundary>
                            <Settings />
                          </RouteErrorBoundary>
                        } 
                      />
                      
                      {/* Research Routes */}
                      <Route 
                        path="/research/trends" 
                        element={
                          <RouteErrorBoundary>
                            <TrendAnalysis />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/research/competitors" 
                        element={
                          <RouteErrorBoundary>
                            <CompetitorAnalysis />
                          </RouteErrorBoundary>
                        } 
                      />
                      
                      {/* AI Insights Routes */}
                      <Route 
                        path="/ai-insights" 
                        element={
                          <RouteErrorBoundary>
                            <AIDashboard />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/ai-insights/recommendations" 
                        element={
                          <RouteErrorBoundary>
                            <AIRecommendations />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/ai-insights/price-optimization" 
                        element={
                          <RouteErrorBoundary>
                            <PriceOptimization />
                          </RouteErrorBoundary>
                        } 
                      />
                      <Route 
                        path="/ai-insights/demand-forecast" 
                        element={
                          <RouteErrorBoundary>
                            <DemandForecast />
                          </RouteErrorBoundary>
                        } 
                      />
                      
                      {/* Monitoring Routes */}
                      <Route 
                        path="/monitoring" 
                        element={
                          <RouteErrorBoundary>
                            <SystemMonitoring />
                          </RouteErrorBoundary>
                        } 
                      />
                    </Route>
                  </Routes>
                </Router>
                
                {/* 알림 시스템 */}
                <NotificationCenter />
                
                {/* 고객 지원 챗봇 */}
                <CustomerSupportChat position="bottom-right" />
                
                {/* 기존 Toast 시스템 (호환성 유지) */}
                <Toaster
                  position="top-left"
                  toastOptions={{
                    duration: 3000,
                    style: {
                      background: '#333',
                      color: '#fff',
                    },
                  }}
                />
              </NotificationProvider>
            </LocalizationProvider>
          </ThemeProvider>
          </WebSocketSyncWrapper>
        </QueryClientProvider>
      </Provider>
    </ErrorBoundary>
  )
}

export default App