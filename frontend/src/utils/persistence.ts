/**
 * 데이터 지속성 유틸리티
 * localStorage를 사용한 사용자 데이터 저장/복원
 */

import React from 'react'

export interface PersistentStore<T> {
  get(): T
  set(value: T): void
  update(updater: (current: T) => T): void
  clear(): void
  subscribe(callback: (value: T) => void): () => void
}

/**
 * localStorage 기반 지속 저장소 생성
 */
export function createPersistentStore<T>(
  key: string, 
  defaultValue: T,
  options?: {
    serialize?: (value: T) => string
    deserialize?: (value: string) => T
    version?: string
  }
): PersistentStore<T> {
  const serialize = options?.serialize || JSON.stringify
  const deserialize = options?.deserialize || JSON.parse
  const storageKey = options?.version ? `${key}_v${options.version}` : key
  
  const subscribers = new Set<(value: T) => void>()

  const get = (): T => {
    try {
      const stored = localStorage.getItem(storageKey)
      if (stored === null) {
        return defaultValue
      }
      return deserialize(stored)
    } catch (error) {
      console.warn(`Failed to load data from localStorage for key "${storageKey}":`, error)
      return defaultValue
    }
  }

  const set = (value: T): void => {
    try {
      localStorage.setItem(storageKey, serialize(value))
      // 구독자들에게 변경 알림
      subscribers.forEach(callback => callback(value))
    } catch (error) {
      console.error(`Failed to save data to localStorage for key "${storageKey}":`, error)
      // 저장 공간 부족 시 사용자에게 알림
      if ((error as Error).name === 'QuotaExceededError') {
        console.warn('localStorage quota exceeded. Consider clearing old data.')
      }
    }
  }

  const update = (updater: (current: T) => T): void => {
    const current = get()
    const updated = updater(current)
    set(updated)
  }

  const clear = (): void => {
    localStorage.removeItem(storageKey)
    subscribers.forEach(callback => callback(defaultValue))
  }

  const subscribe = (callback: (value: T) => void): (() => void) => {
    subscribers.add(callback)
    return () => {
      subscribers.delete(callback)
    }
  }

  return { get, set, update, clear, subscribe }
}

/**
 * React Hook으로 지속 상태 관리
 */
export function usePersistentState<T>(
  key: string, 
  defaultValue: T,
  options?: Parameters<typeof createPersistentStore>[2]
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const store = React.useMemo(
    () => createPersistentStore(key, defaultValue, options),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key]
  )
  
  const [state, setState] = React.useState<T>(() => store.get())

  React.useEffect(() => {
    // Get current value first
    setState(store.get())
    // Then subscribe to changes
    const unsubscribe = store.subscribe((value: T) => setState(value))
    return unsubscribe
  }, [store])

  const setValue = React.useCallback((value: T | ((prev: T) => T)) => {
    if (typeof value === 'function') {
      store.update(value as (prev: T) => T)
    } else {
      store.set(value)
    }
  }, [store])

  const clearValue = React.useCallback(() => {
    store.clear()
  }, [store])

  return [state, setValue, clearValue]
}

/**
 * 데이터 마이그레이션 헬퍼
 */
export function migrateStorageData(
  oldKey: string, 
  newKey: string, 
  migrator?: (oldData: any) => any
): boolean {
  try {
    const oldData = localStorage.getItem(oldKey)
    if (oldData) {
      const parsed = JSON.parse(oldData)
      const migrated = migrator ? migrator(parsed) : parsed
      localStorage.setItem(newKey, JSON.stringify(migrated))
      localStorage.removeItem(oldKey)
      return true
    }
    return false
  } catch (error) {
    console.error('Migration failed:', error)
    return false
  }
}

/**
 * 저장 공간 사용량 체크
 */
export function getStorageInfo(): {
  used: number
  available: number
  percentage: number
} {
  try {
    // 대략적인 사용량 계산
    let used = 0
    for (let key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        used += localStorage[key].length + key.length
      }
    }
    
    // 대부분 브라우저에서 localStorage는 5-10MB 제한
    const available = 5 * 1024 * 1024 // 5MB 가정
    const percentage = (used / available) * 100

    return { used, available, percentage }
  } catch (error) {
    return { used: 0, available: 0, percentage: 0 }
  }
}