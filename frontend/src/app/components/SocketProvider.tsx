"use client";

import React, { createContext, useContext, ReactNode } from "react";
import { useAnalytics, AnalyticsPayload } from "../hooks/useAnalytics";

interface SocketContextType {
  data: AnalyticsPayload | null;
  isConnected: boolean;
  error: string | null;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

export function SocketProvider({ children }: { children: ReactNode }) {
  const { data, isConnected, error } = useAnalytics();

  return (
    <SocketContext.Provider value={{ data, isConnected, error }}>
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
