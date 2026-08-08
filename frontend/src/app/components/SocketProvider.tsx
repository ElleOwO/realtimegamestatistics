"use client";

import React, { createContext, useContext, ReactNode } from "react";
import { useAnalytics, AnalyticsPayload, LiveCommand } from "../hooks/useAnalytics";

interface SocketContextType {
  data: AnalyticsPayload | null;
  isConnected: boolean;
  error: string | null;
  sendCommand: (command: LiveCommand) => boolean;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

export function SocketProvider({ children }: { children: ReactNode }) {
  const { data, isConnected, error, sendCommand } = useAnalytics();

  return (
    <SocketContext.Provider value={{ data, isConnected, error, sendCommand }}>
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
}
