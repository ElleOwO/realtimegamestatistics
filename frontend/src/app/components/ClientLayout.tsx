"use client";

import { usePathname } from "next/navigation";
import { Navigation } from "./Navigation";

import { SocketProvider } from "./SocketProvider";

export function ClientLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const isOverview = pathname === "/";

  return (
    <SocketProvider>
      <div
        className={`${isOverview ? "h-screen overflow-hidden" : "min-h-screen"} bg-background text-foreground antialiased font-serif flex flex-col`}
      >
        <Navigation />
        <main className={`${isOverview ? "flex-1 min-h-0" : ""} p-4`}>{children}</main>
      </div>
    </SocketProvider>
  );
}
