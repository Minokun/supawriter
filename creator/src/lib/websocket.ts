import { useAuthStore } from '@store/authStore'

type MessageHandler = (data: any) => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectTimeout: NodeJS.Timeout | null = null
  private handlers: Map<string, Set<MessageHandler>> = new Map()
  private heartbeatInterval: NodeJS.Timeout | null = null

  connect(userId: string) {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws'
    const token = useAuthStore.getState().token

    // 构建 WebSocket URL（带 token）
    const url = `${wsUrl}?token=${token}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0

      // 启动心跳
      this.startHeartbeat()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // 处理 ping
        if (data.type === 'ping') {
          this.send({ type: 'pong' })
          return
        }

        // 分发消息到处理器
        const handlers = this.handlers.get(data.type)
        if (handlers) {
          handlers.forEach(handler => handler(data))
        }

        // 分发到所有处理器（用于通配符处理）
        const allHandlers = this.handlers.get('*')
        if (allHandlers) {
          allHandlers.forEach(handler => handler(data))
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.stopHeartbeat()
      this.reconnect()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)

      console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

      this.reconnectTimeout = setTimeout(() => {
        const token = useAuthStore.getState().token
        if (token) {
          // 获取用户 ID 并重连
          // TODO: 从 token 解析用户 ID
          this.connect('user')
        }
      }, delay)
    } else {
      console.error('Max reconnection attempts reached')
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' })
      }
    }, 30000) // 每 30 秒发送一次心跳
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)

    // 返回清理函数
    return () => {
      this.off(type, handler)
    }
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  disconnect() {
    this.stopHeartbeat()

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.handlers.clear()
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// 全局 WebSocket 客户端实例
let wsClient: WebSocketClient | null = null

export const getWebSocketClient = (): WebSocketClient => {
  if (!wsClient) {
    wsClient = new WebSocketClient()
  }
  return wsClient
}

export const connectWebSocket = (userId: string) => {
  const client = getWebSocketClient()
  client.connect(userId)
  return client
}

export const disconnectWebSocket = () => {
  if (wsClient) {
    wsClient.disconnect()
    wsClient = null
  }
}
