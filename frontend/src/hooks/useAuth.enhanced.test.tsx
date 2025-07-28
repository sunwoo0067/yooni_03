/**
 * useAuth 훅 향상된 테스트
 */
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth } from './useAuth'

describe('useAuth 훅', () => {
  it('초기 상태가 올바르게 설정된다', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toEqual({
      id: 1,
      email: 'admin@yooni.com',
      name: 'Admin User'
    })
    expect(result.current.loading).toBe(false)
    expect(result.current.sessionExpiry).toBe(null)
  })

  it('사용자 정보가 정상적으로 반환된다', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.user.email).toBe('admin@yooni.com')
    expect(result.current.user.name).toBe('Admin User')
  })

  it('항상 인증된 상태를 반환한다', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(true)
  })

  it('로딩 상태가 false를 반환한다', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.loading).toBe(false)
  })
})