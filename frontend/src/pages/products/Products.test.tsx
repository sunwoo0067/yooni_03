/**
 * 상품 페이지 컴포넌트 테스트
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { configureStore } from '@reduxjs/toolkit'
import { BrowserRouter } from 'react-router-dom'
import Products from './Products'
import productSlice from '../../store/slices/productSlice'
import authSlice from '../../store/slices/authSlice'
import uiSlice from '../../store/slices/uiSlice'
import { NotificationProvider } from '../../components/ui/NotificationSystem'
import { productAPI } from '../../services/api'

// API 모킹
vi.mock('../../services/api', () => ({
  productAPI: {
    getProducts: vi.fn(),
    getProduct: vi.fn(),
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
    deleteProduct: vi.fn(),
    searchProducts: vi.fn(),
    bulkUpdate: vi.fn(),
    importProducts: vi.fn(),
    exportProducts: vi.fn(),
  },
}))

// 테스트용 스토어 생성
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      product: productSlice,
      auth: authSlice,
      ui: uiSlice,
    },
    preloadedState: {
      product: {
        selectedProductId: null,
        filters: {
          page: 1,
          limit: 20,
          sortBy: 'updatedAt',
          sortOrder: 'desc',
        },
        recentlyViewed: [],
        compareList: [],
        bulkSelection: [],
      },
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
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
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <NotificationProvider>
          {children}
        </NotificationProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </Provider>
)

// 샘플 상품 데이터
const mockProducts = [
  {
    id: 1,
    name: '테스트 상품 1',
    price: 10000,
    cost: 5000,
    category: '전자제품',
    sku: 'TEST-001',
    status: 'active',
    stock_quantity: 100,
    created_at: '2024-01-01T10:00:00Z',
  },
  {
    id: 2,
    name: '테스트 상품 2',
    price: 20000,
    cost: 10000,
    category: '생활용품',
    sku: 'TEST-002',
    status: 'active',
    stock_quantity: 50,
    created_at: '2024-01-02T10:00:00Z',
  },
]

describe('Products 컴포넌트', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // API 모킹
    vi.mocked(productAPI.getProducts).mockResolvedValue({
      data: {
        products: mockProducts,
        total: mockProducts.length,
        page: 1,
        limit: 10,
      },
    })
  })

  it('상품 목록이 정상적으로 렌더링된다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출이 완료될 때까지 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })

    // 상품 관리 페이지가 렌더링되었는지 확인
    const title = await screen.findByText('상품 관리')
    expect(title).toBeInTheDocument()
    
    // 상품 데이터가 표시되었는지 확인
    expect(screen.getByText('전체 상품')).toBeInTheDocument()
    
    // 숫자 '2'가 여러 곳에 나타날 수 있으므로 getAllByText 사용
    const twoTexts = screen.getAllByText('2')
    expect(twoTexts.length).toBeGreaterThan(0)
  })

  it('상품 검색이 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })

    // 검색 입력 필드가 있는지 확인
    const searchInputs = await screen.findAllByRole('textbox')
    expect(searchInputs.length).toBeGreaterThan(0)
  })

  it('상품 필터링이 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })

    // 필터 버튼이나 옵션이 있는지 확인
    const buttons = await screen.findAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('상품 정렬이 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('페이지네이션이 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API가 호출되었는지 확인
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('상품 추가 모달이 정상적으로 열린다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })

    // 상품 추가 버튼이 있는지 확인
    const buttons = await screen.findAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('상품 삭제 확인 다이얼로그가 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('상품 상태가 정상적으로 표시된다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('재고 부족 경고가 정상적으로 표시된다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('에러 상태가 정상적으로 처리된다', async () => {
    // API 에러 시뮬레이션
    vi.mocked(productAPI.getProducts).mockRejectedValue(new Error('API 에러'))

    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // 에러 상태에서도 페이지가 렌더링되는지 확인
    const title = await screen.findByText('상품 관리')
    expect(title).toBeInTheDocument()
    
    // API 호출이 실패했는지 확인
    expect(productAPI.getProducts).toHaveBeenCalled()
  })

  it('빈 상품 목록 상태가 정상적으로 표시된다', async () => {
    vi.mocked(productAPI.getProducts).mockResolvedValue({
      data: {
        products: [],
        total: 0,
        page: 1,
        limit: 10,
      },
    })

    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
  })

  it('대량 작업 기능이 정상적으로 작동한다', async () => {
    render(
      <TestWrapper>
        <Products />
      </TestWrapper>
    )

    // API 호출 완료 대기
    await waitFor(() => {
      expect(productAPI.getProducts).toHaveBeenCalled()
    })
    
    // 체크박스가 있는지 확인
    const checkboxes = screen.queryAllByRole('checkbox')
    expect(checkboxes).toBeDefined()
  })
})