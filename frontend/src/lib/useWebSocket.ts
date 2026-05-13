'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

function getWsBase() {
  if (typeof window === 'undefined') return 'ws://localhost:8017';
  const hostname = window.location.hostname;
  if (hostname.includes('trycloudflare.com')) {
    // WebSocket必须连后端Tunnel，不能连前端Tunnel
    return 'wss://booth-five-touched-sellers.trycloudflare.com';
  }
  return `ws://${hostname}:8017`;
}

interface MarketSnapshot {
  type: string;
  timestamp: string;
  sentiment: any;
  strategies: Record<string, any[]>;
  recommendations: any[];
  hot_stocks: any[];
  total_signals: number;
}

export function useMarketWebSocket() {
  const [data, setData] = useState<MarketSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<any>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${getWsBase()}/ws/market`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] 已连接');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'market_snapshot') {
          setData(msg);
        } else if (msg.type === 'ping') {
          ws.send('pong');
        }
      } catch (e) {
        console.error('[WS] 消息解析失败:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[WS] 断开，3秒后重连...');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = (e) => {
      console.error('[WS] 连接错误');
      ws.close();
    };
  }, []);

  const refresh = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('refresh');
    }
  }, []);

  useEffect(() => {
    connect();
    // 心跳保活
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, connected, refresh };
}
