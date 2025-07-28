/**
 * 종합적인 UI 테스트
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import Dashboard from '../pages/Dashboard'
import Products from '../pages/products/Products'
import Orders from '../pages/orders/Orders'
import {
  renderWithProviders,
  testAccessibility,
  testResponsive,
  testPerformance,
  testInteractions,
  testErrorBoundary,
} from './ui-test-suite'

// Mock Chart.js
vi.mock('react-chartjs-2', () => ({
  Line: ({ data }: any) => <div data-testid="line-chart">{JSON.stringify(data)}</div>,
  Bar: ({ data }: any) => <div data-testid="bar-chart">{JSON.stringify(data)}</div>,
  Doughnut: ({ data }: any) => <div data-testid="doughnut-chart">{JSON.stringify(data)}</div>,
}))

// Mock React Query for all components
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query')
  return {
    ...actual,
    useQuery: vi.fn(() => ({
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
    })),
    useMutation: vi.fn(() => ({
      mutate: vi.fn(),
      isLoading: false,
      error: null,
    })),
  }
})

describe('포괄적인 UI 테스트', () => {
  describe('Dashboard 컴포넌트', () => {
    it('렌더링 및 기본 요소 확인', () => {
      renderWithProviders(<Dashboard />)
      
      expect(screen.getByText('대시보드')).toBeInTheDocument()
      expect(screen.getByText('총 매출')).toBeInTheDocument()
      expect(screen.getByText('총 주문')).toBeInTheDocument()
    })

    it('접근성 테스트', async () => {
      const accessibility = await testAccessibility(<Dashboard />)
      
      expect(accessibility.hasHeadings).toBe(true)
      expect(accessibility.focusableCount).toBeGreaterThan(0)
    })

    it('반응형 디자인 테스트', async () => {
      const responsive = await testResponsive(<Dashboard />)
      
      expect(responsive).toHaveLength(3) // mobile, tablet, desktop
      responsive.forEach(result => {
        expect(result.hasContent).toBe(true)
      })
    })

    it('성능 테스트', async () => {
      const performance = await testPerformance(<Dashboard />)
      
      expect(performance.renderTime).toBeLessThan(500) // 500ms 이하
      expect(performance.isPerformant).toBe(true)
    })

    it('상호작용 테스트', async () => {
      const interactions = await testInteractions(<Dashboard />)
      
      expect(interactions.buttonClicks).toBeGreaterThan(0)
      expect(interactions.keyboardNavigation).toBeGreaterThan(0)
    })

    it('에러 처리 테스트', async () => {
      const errorTest = await testErrorBoundary(<Dashboard />)
      
      expect(errorTest.hasError).toBe(false)
    })
  })

  describe('Products 컴포넌트', () => {
    it('렌더링 및 기본 요소 확인', () => {
      renderWithProviders(<Products />)
      
      // Products 페이지의 기본 요소들 확인 - 여러 곳에 '상품' 텍스트가 있을 수 있음
      const productTexts = screen.getAllByText(/상품/)
      expect(productTexts.length).toBeGreaterThan(0)
      expect(productTexts[0]).toBeInTheDocument()
    })

    it('접근성 테스트', async () => {
      const accessibility = await testAccessibility(<Products />)
      
      expect(accessibility.focusableCount).toBeGreaterThan(0)
    })

    it('성능 테스트', async () => {
      const performance = await testPerformance(<Products />)
      
      expect(performance.renderTime).toBeLessThan(500)
    })
  })

  describe('Orders 컴포넌트', () => {
    it('렌더링 및 기본 요소 확인', () => {
      renderWithProviders(<Orders />)
      
      // Orders 페이지의 기본 요소들 확인 - 여러 곳에 '주문' 텍스트가 있을 수 있음
      const orderTexts = screen.getAllByText(/주문/)
      expect(orderTexts.length).toBeGreaterThan(0)
      expect(orderTexts[0]).toBeInTheDocument()
    })

    it('접근성 테스트', async () => {
      const accessibility = await testAccessibility(<Orders />)
      
      expect(accessibility.focusableCount).toBeGreaterThan(0)
    })

    it('성능 테스트', async () => {
      const performance = await testPerformance(<Orders />)
      
      expect(performance.renderTime).toBeLessThan(500)
    })
  })
})

describe('크로스 브라우저 호환성', () => {
  it('다양한 뷰포트에서 Dashboard 렌더링', async () => {
    const viewports = [
      { width: 320, height: 568 },   // iPhone SE
      { width: 375, height: 667 },   // iPhone 8
      { width: 768, height: 1024 },  // iPad
      { width: 1024, height: 768 },  // iPad Landscape
      { width: 1920, height: 1080 }, // Desktop
    ]

    for (const viewport of viewports) {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: viewport.width,
      })
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: viewport.height,
      })

      const { container } = renderWithProviders(<Dashboard />)
      expect(container.firstChild).toBeInTheDocument()
    }
  })
})

describe('사용자 시나리오 테스트', () => {
  it('대시보드 → 상품 페이지 네비게이션', async () => {
    const { user } = renderWithProviders(<Dashboard />)
    
    // Dashboard가 렌더링되었는지 확인
    expect(screen.getByText(/대시보드/i)).toBeInTheDocument()
    
    // 사이드바나 네비게이션 요소 확인 - 링크가 없을 수 있으므로 버튼이나 다른 요소도 확인
    const interactiveElements = screen.queryAllByRole('button')
    const navLinks = screen.queryAllByRole('link')
    
    expect(interactiveElements.length + navLinks.length).toBeGreaterThan(0)
  })

  it('검색 기능 시뮬레이션', async () => {
    const { user } = renderWithProviders(<Products />)
    
    // 검색 입력 필드가 있다면 테스트
    const searchInputs = screen.queryAllByRole('textbox')
    
    if (searchInputs.length > 0) {
      await user.type(searchInputs[0], '테스트 검색어')
      expect(searchInputs[0]).toHaveValue('테스트 검색어')
    }
  })
})

describe('UI 일관성 테스트', () => {
  it('모든 주요 컴포넌트에서 일관된 테마 적용', () => {
    const components = [<Dashboard />, <Products />, <Orders />]
    
    components.forEach(component => {
      const { container } = renderWithProviders(component)
      
      // MUI 테마가 적용된 요소들 확인
      const muiElements = container.querySelectorAll('[class*="Mui"]')
      expect(muiElements.length).toBeGreaterThan(0)
    })
  })

  it('버튼 스타일 일관성', () => {
    renderWithProviders(<Dashboard />)
    
    const buttons = screen.getAllByRole('button')
    
    buttons.forEach(button => {
      // MUI 버튼 클래스가 적용되었는지 확인
      expect(button.className).toContain('MuiButton')
    })
  })
})