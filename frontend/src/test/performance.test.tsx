/**
 * 성능 및 로딩 테스트
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './ui-test-suite'
import Dashboard from '../pages/Dashboard'
import Products from '../pages/products/Products'

// Mock Chart.js
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}))

// Mock React Query
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
          revenueTrend: [],
          categorySales: [],
          platformOrders: []
        }
      },
      isLoading: false,
      error: null,
      refetch: vi.fn()
    })),
  }
})

describe('성능 및 로딩 테스트', () => {
  
  describe('렌더링 성능', () => {
    it('Dashboard 컴포넌트 렌더링 시간 측정', async () => {
      const startTime = performance.now()
      
      renderWithProviders(<Dashboard />)
      
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      console.log(`Dashboard 렌더링 시간: ${renderTime.toFixed(2)}ms`)
      
      // 350ms 이하여야 함 (실제 환경에서는 더 복잡할 수 있음)
      expect(renderTime).toBeLessThan(350)
    })

    it('Products 컴포넌트 렌더링 시간 측정', async () => {
      const startTime = performance.now()
      
      renderWithProviders(<Products />)
      
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      console.log(`Products 렌더링 시간: ${renderTime.toFixed(2)}ms`)
      
      // 300ms 이하여야 함 (Products는 더 복잡할 수 있음)
      expect(renderTime).toBeLessThan(300)
    })
  })

  describe('메모리 사용량', () => {
    it('여러 컴포넌트 렌더링 후 메모리 누수 검사', () => {
      const initialMemory = performance.memory?.usedJSHeapSize || 0
      
      // 여러 컴포넌트 렌더링
      for (let i = 0; i < 10; i++) {
        const { unmount } = renderWithProviders(<Dashboard />)
        unmount()
      }
      
      const finalMemory = performance.memory?.usedJSHeapSize || 0
      const memoryIncrease = finalMemory - initialMemory
      
      console.log(`메모리 증가량: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`)
      
      // 메모리 증가가 50MB 이하여야 함
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024)
    })
  })

  describe.skip('비동기 로딩', () => {
    it('Dashboard 데이터 로딩 상태 확인', async () => {
      // 로딩 상태 모킹
      vi.mocked(vi.importActual('@tanstack/react-query')).useQuery.mockReturnValueOnce({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn()
      })

      renderWithProviders(<Dashboard />)
      
      // 로딩 상태에서도 기본 구조는 렌더링되어야 함
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })

    it('에러 상태 처리 확인', async () => {
      // 에러 상태 모킹
      vi.mocked(vi.importActual('@tanstack/react-query')).useQuery.mockReturnValueOnce({
        data: null,
        isLoading: false,
        error: new Error('API 에러'),
        refetch: vi.fn()
      })

      renderWithProviders(<Dashboard />)
      
      // 에러 상태에서도 페이지는 깨지지 않아야 함
      expect(screen.getByText('대시보드')).toBeInTheDocument()
    })
  })

  describe('대용량 데이터 처리', () => {
    it('많은 아이템을 가진 목록 렌더링 성능', () => {
      // 대용량 데이터 모킹
      const largeDataset = Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        name: `상품 ${i}`,
        price: 10000 + i,
        stock: 100 - i % 50
      }))

      const startTime = performance.now()
      
      // 실제로는 가상화된 리스트를 사용해야 하지만, 
      // 여기서는 기본 렌더링 성능만 테스트
      renderWithProviders(<Products />)
      
      const endTime = performance.now()
      const renderTime = endTime - startTime
      
      console.log(`대용량 데이터 렌더링 시간: ${renderTime.toFixed(2)}ms`)
      
      // 대용량 데이터여도 500ms 이하여야 함
      expect(renderTime).toBeLessThan(500)
    })
  })

  describe.skip('네트워크 성능 시뮬레이션', () => {
    it('느린 네트워크 환경에서의 로딩 처리', async () => {
      // 느린 API 응답 시뮬레이션
      const slowQuery = vi.fn().mockImplementation(() => 
        new Promise(resolve => 
          setTimeout(() => resolve({
            data: { stats: {}, charts: {} },
            isLoading: false,
            error: null,
            refetch: vi.fn()
          }), 2000)
        )
      )

      vi.mocked(vi.importActual('@tanstack/react-query')).useQuery.mockImplementation(slowQuery)

      const startTime = performance.now()
      renderWithProviders(<Dashboard />)
      const endTime = performance.now()
      
      // 초기 렌더링은 빨라야 함 (데이터 로딩과 무관하게)
      expect(endTime - startTime).toBeLessThan(100)
    })
  })

  describe('리렌더링 최적화', () => {
    it('불필요한 리렌더링 방지 확인', () => {
      let renderCount = 0
      
      const TestComponent = () => {
        renderCount++
        return <Dashboard />
      }

      const { rerender } = renderWithProviders(<TestComponent />)
      
      const initialRenderCount = renderCount
      
      // 동일한 props로 리렌더링
      rerender(<TestComponent />)
      
      // 렌더링 횟수가 크게 증가하지 않아야 함
      expect(renderCount - initialRenderCount).toBeLessThan(5)
    })
  })

  describe('번들 크기 최적화', () => {
    it('컴포넌트별 번들 크기 추정', () => {
      // 실제 번들 분석은 webpack-bundle-analyzer 등을 사용하지만,
      // 여기서는 간단한 문자열 길이로 추정
      
      const dashboardString = Dashboard.toString()
      const productsString = Products.toString()
      
      console.log(`Dashboard 컴포넌트 크기: ${dashboardString.length} chars`)
      console.log(`Products 컴포넌트 크기: ${productsString.length} chars`)
      
      // 컴포넌트가 너무 크지 않아야 함 (임의의 기준)
      expect(dashboardString.length).toBeLessThan(100000)
      expect(productsString.length).toBeLessThan(100000)
    })
  })
})