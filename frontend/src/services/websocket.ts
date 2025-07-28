// Event-based communication - no direct Redux imports

export interface WebSocketMessage {
  type: string
  changeType?: string
  data?: any
  topic?: string
  timestamp?: string
}

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectInterval: number = 5000
  private maxReconnectAttempts: number = 5
  private reconnectAttempts: number = 0
  private heartbeatInterval: NodeJS.Timeout | null = null
  private isIntentionallyClosed: boolean = false
  private subscribers: Map<string, Set<(message: WebSocketMessage) => void>> = new Map()

  constructor() {
    // WebSocket URL 설정
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${wsProtocol}//localhost:8000/ws`
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    this.isIntentionallyClosed = false
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected')
      this.reconnectAttempts = 0
      
      // Subscribe to topics
      this.subscribe('products')
      this.subscribe('orders')
      this.subscribe('platforms')
      
      // Start heartbeat
      this.startHeartbeat()
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        this.handleMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.stopHeartbeat()
      
      if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        setTimeout(() => this.connect(), this.reconnectInterval)
      }
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' })
      }
    }, 30000) // 30초마다 ping
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  private subscribe(topic: string): void {
    this.send({ type: 'subscribe', topic })
  }

  unsubscribe(topic: string): void {
    this.send({ type: 'unsubscribe', topic })
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('📨 WebSocket message:', message)

    // Notify subscribers
    const subscribers = this.subscribers.get(message.type)
    if (subscribers) {
      subscribers.forEach(callback => callback(message))
    }

    // Handle specific message types
    switch (message.type) {
      case 'data_change':
        this.handleDataChange(message)
        break
      case 'subscribed':
        console.log(`Subscribed to topic: ${message.topic}`)
        break
      case 'pong':
        // Heartbeat response
        break
    }
  }

  private handleDataChange(message: WebSocketMessage): void {
    const { changeType, data } = message

    // Emit custom events for React components to handle
    const event = new CustomEvent('websocket:dataChange', {
      detail: { changeType, data }
    })
    window.dispatchEvent(event)

    // Handle notification display
    switch (changeType) {
      case 'product_created':
        this.showNotification('success', '새 상품 추가됨', `${data.name}이(가) 추가되었습니다.`)
        break
      
      case 'product_updated':
        this.showNotification('info', '상품 업데이트됨', `${data.name}이(가) 업데이트되었습니다.`)
        break
      
      case 'product_deleted':
        this.showNotification('warning', '상품 삭제됨', '상품이 삭제되었습니다.')
        break
      
      case 'order_created':
        this.showNotification('success', '새 주문 접수', `주문번호 ${data.order_number}`)
        break
      
      case 'platform_sync':
        this.showNotification('info', '플랫폼 동기화', `${data.platform} 동기화 ${data.status}`)
        break
    }
  }

  private showNotification(type: string, title: string, message: string): void {
    // 간단한 콘솔 로그로 대체 (실제로는 NotificationSystem 사용)
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`)
  }

  // Subscribe to specific message types
  on(type: string, callback: (message: WebSocketMessage) => void): () => void {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set())
    }
    this.subscribers.get(type)!.add(callback)

    // Return unsubscribe function
    return () => {
      const subscribers = this.subscribers.get(type)
      if (subscribers) {
        subscribers.delete(callback)
      }
    }
  }
}

// Singleton instance
export const websocketService = new WebSocketService()

// Auto-connect when imported
if (typeof window !== 'undefined') {
  websocketService.connect()
  
  // Reconnect on window focus
  window.addEventListener('focus', () => {
    websocketService.connect()
  })
  
  // Disconnect on window unload
  window.addEventListener('beforeunload', () => {
    websocketService.disconnect()
  })
}