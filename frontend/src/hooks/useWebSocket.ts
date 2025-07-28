import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface WebSocketMessage {
  type: string;
  data?: any;
  channel?: string;
  timestamp?: string;
}

interface WebSocketState {
  connected: boolean;
  metrics: any;
  alerts: any[];
  systemStatus: any;
  error: string | null;
}

export function useWebSocket() {
  const { user } = useAuth();
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    metrics: null,
    alerts: [],
    systemStatus: null,
    error: null,
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const subscriptions = useRef<Set<string>>(new Set());

  const connect = useCallback(() => {
    if (!user?.id) return;

    try {
      // Clear any existing connection
      if (ws.current) {
        ws.current.close();
      }

      // Create WebSocket connection
      const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/api/v1/dashboard/ws/${user.id}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({ ...prev, connected: true, error: null }));
        reconnectAttempts.current = 0;

        // Send heartbeat
        const heartbeat = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);

        ws.current.addEventListener('close', () => {
          clearInterval(heartbeat);
        });

        // Resubscribe to channels
        if (subscriptions.current.size > 0) {
          ws.current.send(JSON.stringify({
            type: 'subscribe',
            metrics: Array.from(subscriptions.current),
          }));
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, error: 'Connection error' }));
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setState(prev => ({ ...prev, connected: false }));

        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          
          console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttempts.current})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setState(prev => ({ ...prev, error: 'Failed to connect' }));
    }
  }, [user?.id]);

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'connection':
        console.log('Connection confirmed:', message);
        break;

      case 'pong':
        // Heartbeat response
        break;

      case 'dashboard_update':
        if (message.data) {
          setState(prev => ({ ...prev, metrics: message.data }));
        }
        break;

      case 'new_alert':
        if (message.data?.alert) {
          setState(prev => ({
            ...prev,
            alerts: [message.data.alert, ...prev.alerts],
          }));
        }
        break;

      case 'alert_update':
        if (message.data?.alert) {
          setState(prev => ({
            ...prev,
            alerts: prev.alerts.map(alert =>
              alert.id === message.data.alert.id ? message.data.alert : alert
            ),
          }));
        }
        break;

      case 'system_status':
        if (message.data) {
          setState(prev => ({ ...prev, systemStatus: message.data }));
        }
        break;

      case 'data':
        // Handle channel-specific data
        if (message.channel && message.data) {
          handleChannelData(message.channel, message.data);
        }
        break;

      case 'error':
        console.error('WebSocket error message:', message);
        setState(prev => ({ ...prev, error: message.data?.message || 'Unknown error' }));
        break;

      default:
        console.log('Unknown message type:', message);
    }
  };

  const handleChannelData = (channel: string, data: any) => {
    // Handle channel-specific data updates
    switch (channel) {
      case 'metrics':
        setState(prev => ({ ...prev, metrics: data }));
        break;
      case 'alerts':
        setState(prev => ({ ...prev, alerts: data }));
        break;
      // Add more channels as needed
    }
  };

  const subscribe = useCallback((channels: string[]) => {
    channels.forEach(channel => subscriptions.current.add(channel));
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        metrics: channels,
      }));
    }
  }, []);

  const unsubscribe = useCallback((channels: string[]) => {
    channels.forEach(channel => subscriptions.current.delete(channel));
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'unsubscribe',
        metrics: channels,
      }));
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  const refresh = useCallback((refreshType: string) => {
    sendMessage({
      type: 'refresh',
      refresh_type: refreshType,
    });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return {
    connected: state.connected,
    metrics: state.metrics,
    alerts: state.alerts,
    systemStatus: state.systemStatus,
    error: state.error,
    subscribe,
    unsubscribe,
    sendMessage,
    refresh,
  };
}