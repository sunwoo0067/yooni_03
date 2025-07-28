import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth } from './useAuth'

describe('useAuth', () => {
  it('returns authenticated state', () => {
    const { result } = renderHook(() => useAuth())
    
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.loading).toBe(false)
    expect(result.current.user).toEqual({
      id: 1,
      email: 'admin@yooni.com',
      name: 'Admin User'
    })
    expect(result.current.sessionExpiry).toBe(null)
  })
})