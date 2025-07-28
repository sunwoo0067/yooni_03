/**
 * 포괄적인 UI 테스트 스위트
 * 컴포넌트 렌더링, 상호작용, 접근성 등을 테스트
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import { configureStore } from '@reduxjs/toolkit'
import React from 'react'
import { NotificationProvider } from '../components/ui/NotificationSystem'

// 테스트용 래퍼 컴포넌트
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const mockStore = configureStore({
    reducer: {
      ui: () => ({ sidebarOpen: true, theme: 'light' }),
      product: () => ({ products: [], loading: false }),
      auth: () => ({ user: null, isAuthenticated: false }),
    },
  })

  const theme = createTheme()

  return (
    <Provider store={mockStore}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <NotificationProvider>
            <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
              {children}
            </BrowserRouter>
          </NotificationProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  )
}

// 공통 테스트 유틸리티
export const renderWithProviders = (component: React.ReactElement) => {
  return {
    user: userEvent.setup(),
    ...render(component, { wrapper: TestWrapper }),
  }
}

// 접근성 테스트 헬퍼
export const testAccessibility = async (component: React.ReactElement) => {
  const { container } = renderWithProviders(component)
  
  // 기본 접근성 검사
  expect(container.firstChild).toBeInTheDocument()
  
  // 키보드 내비게이션 가능한 요소들 확인
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  
  return {
    focusableCount: focusableElements.length,
    hasHeadings: container.querySelectorAll('h1, h2, h3, h4, h5, h6').length > 0,
    hasLandmarks: container.querySelectorAll('[role="main"], [role="navigation"], [role="banner"]').length > 0,
  }
}

// 반응형 테스트 헬퍼
export const testResponsive = async (component: React.ReactElement) => {
  const breakpoints = [
    { width: 320, height: 568, name: 'mobile' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 1200, height: 800, name: 'desktop' },
  ]

  const results = []

  for (const bp of breakpoints) {
    // 뷰포트 크기 변경 시뮬레이션
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: bp.width,
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: bp.height,
    })

    window.dispatchEvent(new Event('resize'))
    
    const { container } = renderWithProviders(component)
    
    results.push({
      breakpoint: bp.name,
      width: bp.width,
      height: bp.height,
      hasContent: (container.textContent?.length || 0) > 0,
      hasInteractiveElements: container.querySelectorAll('button, input, select').length > 0,
    })
  }

  return results
}

// 성능 테스트 헬퍼
export const testPerformance = async (component: React.ReactElement) => {
  const startTime = performance.now()
  
  renderWithProviders(component)
  
  const endTime = performance.now()
  const renderTime = endTime - startTime
  
  return {
    renderTime,
    isPerformant: renderTime < 100, // 100ms 이하면 양호
  }
}

// 상호작용 테스트 헬퍼
export const testInteractions = async (component: React.ReactElement) => {
  const { user } = renderWithProviders(component)
  
  const buttons = screen.queryAllByRole('button')
  const links = screen.queryAllByRole('link')
  const inputs = screen.queryAllByRole('textbox')
  
  const interactions = {
    buttonClicks: 0,
    linkClicks: 0,
    inputFocus: 0,
    keyboardNavigation: 0,
  }

  // 버튼 클릭 테스트
  for (const button of buttons.slice(0, 3)) { // 처음 3개만 테스트
    try {
      await user.click(button)
      interactions.buttonClicks++
    } catch (error) {
      // 클릭할 수 없는 버튼은 무시
    }
  }

  // 입력 필드 포커스 테스트
  for (const input of inputs.slice(0, 2)) { // 처음 2개만 테스트
    try {
      await user.click(input)
      interactions.inputFocus++
    } catch (error) {
      // 포커스할 수 없는 입력은 무시
    }
  }

  // 키보드 내비게이션 테스트
  try {
    await user.keyboard('{Tab}')
    await user.keyboard('{Tab}')
    interactions.keyboardNavigation = 2
  } catch (error) {
    // 키보드 내비게이션 실패는 무시
  }

  return interactions
}

// 에러 바운더리 테스트 헬퍼
export const testErrorBoundary = async (component: React.ReactElement) => {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  
  try {
    renderWithProviders(component)
    return { hasError: false }
  } catch (error) {
    return { hasError: true, error }
  } finally {
    consoleSpy.mockRestore()
  }
}

export default {
  renderWithProviders,
  testAccessibility,
  testResponsive,
  testPerformance,
  testInteractions,
  testErrorBoundary,
}