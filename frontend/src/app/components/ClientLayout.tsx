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
      <div className="min-h-screen bg-background text-foreground antialiased font-serif flex flex-col">
        <Navigation />
        <main className="flex-1 p-4">{children}</main>
      </div>
    </SocketProvider>
  );
}
