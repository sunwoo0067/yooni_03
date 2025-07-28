import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './Dashboard'

// Mock Redux store
const mockStore = configureStore({
  reducer: {
    ui: () => ({
      sidebarOpen: true,
      theme: 'light'
    }),
    product: () => ({
      products: [],
      loading: false
    })
  }
})

// Create QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
})

// Mock Chart.js
vi.mock('react-chartjs-2', () => ({
  Line: () => null,
  Bar: () => null,
  Doughnut: () => null,
}))

// Mock React Query
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query')
  return {
    ...actual,
    useQuery: () => ({
      data: {
        stats: {
          totalRevenue: 15234500,
          totalOrders: 342,
          totalCustomers: 1250,
          totalProducts: 485
        },
        charts: {
          revenueTrend: [
            { date: '2024-01', revenue: 1000000 },
            { date: '2024-02', revenue: 1200000 }
          ],
          categorySales: [
            { category: '전자기기', value: 5000000 },
            { category: '의류', value: 3000000 }
          ],
          platformOrders: [
            { platform: '쿠팡', orders: 150 },
            { platform: '네이버', orders: 120 }
          ]
        }
      },
      isLoading: false,
      error: null,
      refetch: vi.fn()
    })
  }
})

describe('Dashboard', () => {
  it('renders dashboard title', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Provider store={mockStore}>
          <Dashboard />
        </Provider>
      </QueryClientProvider>
    )
    
    expect(screen.getByText('대시보드')).toBeInTheDocument()
  })

  it('renders stat cards', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Provider store={mockStore}>
          <Dashboard />
        </Provider>
      </QueryClientProvider>
    )
    
    expect(screen.getByText('총 매출')).toBeInTheDocument()
    expect(screen.getByText('총 주문')).toBeInTheDocument()
    expect(screen.getByText('상품 수')).toBeInTheDocument()
    expect(screen.getByText('고객 수')).toBeInTheDocument()
  })

  it('renders chart sections', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Provider store={mockStore}>
          <Dashboard />
        </Provider>
      </QueryClientProvider>
    )
    
    // Dashboard uses react-grid-layout, check for grid layout wrapper
    expect(screen.getByTestId('grid-layout')).toBeInTheDocument()
    
    // Check for chart containers - use getAllByTestId since there are multiple
    const chartContainers = screen.getAllByTestId('responsive-container')
    expect(chartContainers.length).toBeGreaterThan(0)
  })
})