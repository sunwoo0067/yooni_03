import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { websocketService } from '@services/websocket'

// WebSocket 이벤트와 React Query를 동기화하는 훅
export const useWebSocketSync = () => {
  const queryClient = useQueryClient()

  useEffect(() => {
    // WebSocket 데이터 변경 이벤트 처리
    const handleDataChange = (event: CustomEvent) => {
      const { changeType, data } = event.detail

      switch (changeType) {
        case 'product_created':
        case 'product_updated':
        case 'product_deleted':
          // 상품 관련 쿼리 무효화
          queryClient.invalidateQueries({ queryKey: ['products'] })
          break

        case 'order_created':
        case 'order_updated':
        case 'order_deleted':
          // 주문 관련 쿼리 무효화
          queryClient.invalidateQueries({ queryKey: ['orders'] })
          break

        case 'platform_sync':
          // 플랫폼 관련 쿼리 무효화
          queryClient.invalidateQueries({ queryKey: ['platforms'] })
          break

        case 'inventory_update':
          // 재고 관련 쿼리 무효화
          queryClient.invalidateQueries({ queryKey: ['inventory'] })
          break
      }
    }

    // 이벤트 리스너 등록
    window.addEventListener('websocket:dataChange', handleDataChange as EventListener)

    // WebSocket 연결 보장
    websocketService.connect()

    // 클린업
    return () => {
      window.removeEventListener('websocket:dataChange', handleDataChange as EventListener)
    }
  }, [queryClient])
}