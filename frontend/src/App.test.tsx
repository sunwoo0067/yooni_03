import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import App from './App'

// Mock API calls
vi.mock('./services/api', () => ({
  default: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  },
  analyticsAPI: {
    getDashboard: vi.fn().mockResolvedValue({ data: {} })
  },
  productAPI: {
    getList: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } })
  }
}))

// Mock WebSocket
vi.mock('./hooks/useWebSocketSync', () => ({
  useWebSocketSync: vi.fn()
}))

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(<App />)
    expect(container).toBeTruthy()
  })
})