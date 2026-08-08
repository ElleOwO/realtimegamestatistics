"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { StreamMessage } from "../types/postgame";
import { API_BASE } from "../lib/postgameApi";

export function useMatchStream(matchId: string, onMessage?: (message: StreamMessage) => void) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<StreamMessage | null>(null);
  const callback = useRef(onMessage);
  callback.current = onMessage;

  const connect = useCallback(() => {
    const wsBase = API_BASE.replace(/^http/, "ws");
    const socket = new WebSocket(`${wsBase}/api/v1/matches/${matchId}/stream`);
    socket.onopen = () => setConnected(true);
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as StreamMessage;
      setLastMessage(message);
      callback.current?.(message);
    };
    socket.onclose = () => setConnected(false);
    return socket;
  }, [matchId]);

  useEffect(() => {
    let socket = connect();
    const interval = window.setInterval(() => {
      if (socket.readyState === WebSocket.CLOSED) socket = connect();
    }, 5000);
    return () => {
      window.clearInterval(interval);
      socket.close();
    };
  }, [connect]);

  return { connected, lastMessage };
}
