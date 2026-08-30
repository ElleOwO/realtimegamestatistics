"use client";

import { Navigation } from "./Navigation";

import { SocketProvider } from "./SocketProvider";

export function ClientLayout({
  children,
  mode,
}: Readonly<{
  children: React.ReactNode;
  mode: "live" | "test" | "replay";
}>) {
  return (
    <SocketProvider>
      <div
        className="flex min-h-screen flex-col bg-background font-sans text-foreground antialiased"
      >
        <Navigation mode={mode} />
        <main className="min-h-0 flex-1">{children}</main>
      </div>
    </SocketProvider>
  );
}
