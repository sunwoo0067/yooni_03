import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAppSelector, useAppDispatch } from '@hooks/redux';
import { setConnectionStatus } from '@store/slices/websocketSlice';
import { SecureStorage } from '@services/storage/SecureStorage';
import { AnalyticsService } from '@services/analytics/AnalyticsService';
import { CrashlyticsService } from '@services/crashlytics/CrashlyticsService';
import Config from 'react-native-config';

interface WebSocketMessage {
  type: string;
  channel: string;
  data: any;
  timestamp: number;
}

interface SubscriptionHandler {
  (data: any): void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  subscribe: (channel: string, handler: SubscriptionHandler) => void;
  unsubscribe: (channel: string, handler: SubscriptionHandler) => void;
  emit: (event: string, data: any) => void;
  reconnect: () => void;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector(state => state.auth);
  const socketRef = useRef<Socket | null>(null);
  const subscriptionsRef = useRef<Map<string, Set<SubscriptionHandler>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);

  // Configuration
  const WS_URL = Config.WS_URL || 'wss://api.yourdomain.com';
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY_BASE = 1000; // 1 second

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const handleConnect = useCallback(() => {
    console.log('WebSocket connected');
    setIsConnected(true);
    dispatch(setConnectionStatus(true));
    reconnectAttemptsRef.current = 0;
    clearReconnectTimeout();

    AnalyticsService.track('websocket_connected');

    // Resubscribe to all channels
    subscriptionsRef.current.forEach((_, channel) => {
      if (socketRef.current) {
        socketRef.current.emit('subscribe', { channel });
      }
    });
  }, [dispatch, clearReconnectTimeout]);

  const handleDisconnect = useCallback((reason: string) => {
    console.log('WebSocket disconnected:', reason);
    setIsConnected(false);
    dispatch(setConnectionStatus(false));

    AnalyticsService.track('websocket_disconnected', { reason });

    // Attempt reconnection with exponential backoff
    if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
      const delay = RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttemptsRef.current);
      reconnectAttemptsRef.current++;

      reconnectTimeoutRef.current = setTimeout(() => {
        if (socketRef.current && !socketRef.current.connected) {
          console.log(`Attempting reconnection (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
          socketRef.current.connect();
        }
      }, delay);
    }
  }, [dispatch]);

  const handleError = useCallback((error: Error) => {
    console.error('WebSocket error:', error);
    CrashlyticsService.recordError(error, 'WebSocket.error');
    AnalyticsService.track('websocket_error', { 
      error: error.message,
      attempts: reconnectAttemptsRef.current,
    });
  }, []);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    const { channel, data } = message;
    const handlers = subscriptionsRef.current.get(channel);

    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in WebSocket handler for channel ${channel}:`, error);
          CrashlyticsService.recordError(error as Error, 'WebSocket.handler');
        }
      });
    }
  }, []);

  const initializeSocket = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      // Get auth token
      const token = await SecureStorage.getItem('accessToken');
      if (!token) {
        console.error('No auth token available for WebSocket');
        return;
      }

      // Create socket connection
      socketRef.current = io(WS_URL, {
        transports: ['websocket'],
        auth: {
          token,
        },
        reconnection: false, // We handle reconnection manually
        timeout: 10000,
        query: {
          platform: 'mobile',
        },
      });

      // Setup event handlers
      socketRef.current.on('connect', handleConnect);
      socketRef.current.on('disconnect', handleDisconnect);
      socketRef.current.on('error', handleError);
      socketRef.current.on('message', handleMessage);

      // Custom events
      socketRef.current.on('auth_error', () => {
        console.error('WebSocket authentication failed');
        socketRef.current?.disconnect();
        // TODO: Handle token refresh
      });

      socketRef.current.on('pong', () => {
        // Keep-alive response
      });

      // Connect
      socketRef.current.connect();
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      CrashlyticsService.recordError(error as Error, 'WebSocket.initialize');
    }
  }, [isAuthenticated, WS_URL, handleConnect, handleDisconnect, handleError, handleMessage]);

  const cleanup = useCallback(() => {
    clearReconnectTimeout();
    
    if (socketRef.current) {
      socketRef.current.removeAllListeners();
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    subscriptionsRef.current.clear();
    setIsConnected(false);
    dispatch(setConnectionStatus(false));
  }, [dispatch, clearReconnectTimeout]);

  const subscribe = useCallback((channel: string, handler: SubscriptionHandler) => {
    // Add handler to subscriptions
    if (!subscriptionsRef.current.has(channel)) {
      subscriptionsRef.current.set(channel, new Set());
    }
    subscriptionsRef.current.get(channel)!.add(handler);

    // Subscribe to channel if connected
    if (socketRef.current?.connected) {
      socketRef.current.emit('subscribe', { channel });
    }

    AnalyticsService.track('websocket_subscribe', { channel });
  }, []);

  const unsubscribe = useCallback((channel: string, handler: SubscriptionHandler) => {
    const handlers = subscriptionsRef.current.get(channel);
    if (handlers) {
      handlers.delete(handler);
      
      // If no more handlers, unsubscribe from channel
      if (handlers.size === 0) {
        subscriptionsRef.current.delete(channel);
        
        if (socketRef.current?.connected) {
          socketRef.current.emit('unsubscribe', { channel });
        }
      }
    }

    AnalyticsService.track('websocket_unsubscribe', { channel });
  }, []);

  const emit = useCallback((event: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
      AnalyticsService.track('websocket_emit', { event });
    } else {
      console.warn('Cannot emit event: WebSocket not connected');
    }
  }, []);

  const reconnect = useCallback(() => {
    cleanup();
    reconnectAttemptsRef.current = 0;
    initializeSocket();
  }, [cleanup, initializeSocket]);

  // Initialize/cleanup on mount/unmount and auth change
  useEffect(() => {
    if (isAuthenticated) {
      initializeSocket();
    } else {
      cleanup();
    }

    return cleanup;
  }, [isAuthenticated, initializeSocket, cleanup]);

  // Keep-alive ping
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (socketRef.current?.connected) {
        socketRef.current.emit('ping');
      }
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(pingInterval);
  }, []);

  return {
    isConnected,
    subscribe,
    unsubscribe,
    emit,
    reconnect,
  };
};