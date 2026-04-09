'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api/backend';

export interface AgentWsEvent {
  type:
    | 'agent_trigger_started'
    | 'agent_trigger_completed'
    | 'agent_draft_ready'
    | 'connected'
    | 'ping';
  agent_id?: string;
  agent_name?: string;
  log_id?: string;
  draft_id?: string;
  drafts_created?: number;
  hotspot_title?: string;
  status?: string;
  error?: string | null;
  message?: string;
}

interface UseAgentWebSocketOptions {
  onTriggerStarted?: (event: AgentWsEvent) => void;
  onTriggerCompleted?: (event: AgentWsEvent) => void;
  onDraftReady?: (event: AgentWsEvent) => void;
  enabled?: boolean;
}

export function useAgentWebSocket(options: UseAgentWebSocketOptions = {}) {
  const { onTriggerStarted, onTriggerCompleted, onDraftReady, enabled = true } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);

  // Store callbacks in refs to avoid reconnect on callback change
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    const token = localStorage.getItem('token');
    if (!token) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const wsUrl = API_URL.replace(/^http/, 'ws') + `/ws?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data: AgentWsEvent = JSON.parse(event.data);

          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          if (data.type === 'agent_trigger_started') {
            callbacksRef.current.onTriggerStarted?.(data);
          } else if (data.type === 'agent_trigger_completed') {
            callbacksRef.current.onTriggerCompleted?.(data);
          } else if (data.type === 'agent_draft_ready') {
            callbacksRef.current.onDraftReady?.(data);
          }
        } catch {
          // Ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Reconnect after 5 seconds
        if (enabled) {
          reconnectTimer.current = setTimeout(connect, 5000);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror
      };
    } catch {
      // Connection failed, will retry
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, connect]);

  return { connected };
}
