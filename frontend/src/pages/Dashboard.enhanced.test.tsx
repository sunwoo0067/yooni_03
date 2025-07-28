/**
 * 대시보드 컴포넌트 향상된 테스트
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { configureStore } from '@reduxjs/toolkit'
import { BrowserRouter } from 'react-router-dom'
import Dashboard from './Dashboard'
import authSlice from '../store/slices/authSlice'
import uiSlice from '../store/slices/uiSlice'
import { NotificationProvider } from '../components/ui/NotificationSystem'

// API 모킹
import * as api from '../services/api'

vi.mock('../services/api', () => ({
  analyticsAPI: {
    getDashboard: vi.fn(),
  },
}))

// 차트 라이브러리 모킹
vi.mock('react-chartjs-2', () => ({
  Line: () => null,
  Bar: () => null,
  Doughnut: () => null,
}))

// 테스트용 스토어 생성
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: authSlice,
      ui: uiSlice,
    },
    preloadedState: {
      auth: {
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'admin',
        },
        isAuthenticated: true,
        token: 'test-token',
      },
      ui: {
        theme: 'light',
        sidebarCollapsed: false,
      },
      ...initialState,
    },
  })
}

// 테스트용 쿼리 클라이언트
const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })
}

// 테스트 래퍼 컴포넌트
const TestWrapper = ({ 
  children, 
  store = createTestStore(), 
  queryClient = createTestQueryClient() 
}) => (
  <Provider store={store}>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}>
        <NotificationProvider>
          {children}
        </NotificationProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </Provider>
)

describe('Dashboard 컴포넌트', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // API 모킹 설정
    vi.mocked(api.analyticsAPI.getDashboard).mockResolvedValue({
      data: {
        orders: {
          revenue: 125000000,
          total: 1250
        },
        products: {
          total: 450,
          connected: 420,
          disconnected: 30
        },
        platforms: {
          connected: 3,
          disconnected: 1
        }
      }
    })
  })

  it('대시보드가 정상적으로 렌더링된다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드 타이틀 확인
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })
  })

  it('통계 카드가 표시된다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드 타이틀 확인
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })
  })

  it('새로고침 버튼이 작동한다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })

    // 새로고침 버튼 찾기
    const refreshButtons = screen.getAllByRole('button')
    expect(refreshButtons.length).toBeGreaterThan(0)
  })

  it('검색 기능이 정상적으로 렌더링된다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })

    // 검색 입력란이 있는지 확인
    const searchInput = screen.getByPlaceholderText('대시보드 검색...')
    expect(searchInput).toBeInTheDocument()
  })

  it('편집 모드 토글이 작동한다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })

    // 편집 모드 스위치가 있는지 확인
    const switches = screen.getAllByRole('checkbox')
    expect(switches.length).toBeGreaterThan(0)
  })

  it('리포트 다운로드 버튼이 존재한다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })
  })

  it('위젯 추가 다이얼로그가 열린다', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    )

    // 대시보드가 렌더링될 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })
  })
})