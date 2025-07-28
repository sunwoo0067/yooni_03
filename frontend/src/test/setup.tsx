import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import React from 'react'

// 각 테스트 후 자동으로 cleanup 실행
afterEach(() => {
  cleanup()
})

// ResizeObserver mock
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn((target) => {
    // 차트 컨테이너에 크기 설정
    if (target) {
      Object.defineProperty(target, 'clientWidth', { value: 800, configurable: true })
      Object.defineProperty(target, 'clientHeight', { value: 400, configurable: true })
      Object.defineProperty(target, 'offsetWidth', { value: 800, configurable: true })
      Object.defineProperty(target, 'offsetHeight', { value: 400, configurable: true })
    }
  }),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// IntersectionObserver mock
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// matchMedia mock
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// WebSocket mock
class MockWebSocket {
  url: string
  readyState: number = 0
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    this.readyState = 1 // OPEN
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    // Mock send
  }

  close() {
    this.readyState = 3 // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }
}

global.WebSocket = MockWebSocket as any

// Mock recharts to avoid size warnings
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  Radar: () => null,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
}))

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Line: ({ data }: any) => <div data-testid="chartjs-line">{JSON.stringify(data)}</div>,
  Bar: ({ data }: any) => <div data-testid="chartjs-bar">{JSON.stringify(data)}</div>,
  Doughnut: ({ data }: any) => <div data-testid="chartjs-doughnut">{JSON.stringify(data)}</div>,
  Pie: ({ data }: any) => <div data-testid="chartjs-pie">{JSON.stringify(data)}</div>,
}))

// Mock react-grid-layout
vi.mock('react-grid-layout', () => {
  const React = require('react')
  return {
    Responsive: ({ children, layouts, onLayoutChange }: any) => {
      // Render children with layout wrapper
      return React.createElement('div', { 'data-testid': 'grid-layout' }, children)
    },
    WidthProvider: (Component: any) => Component,
  }
})

// Mock react-grid-layout CSS
vi.mock('react-grid-layout/css/styles.css', () => ({}))

// localStorage mock
const localStorageMock = {
  getItem: vi.fn((key: string) => null),
  setItem: vi.fn((key: string, value: string) => {}),
  removeItem: vi.fn((key: string) => {}),
  clear: vi.fn(() => {}),
  length: 0,
  key: vi.fn((index: number) => null),
}
global.localStorage = localStorageMock as Storage