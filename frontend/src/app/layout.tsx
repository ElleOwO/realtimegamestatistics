import type { Metadata } from 'next';
import { ClientLayout } from './components/ClientLayout';
import '../styles/index.css';

export const metadata: Metadata = {
  title: 'RTGS Coach Dashboard',
  description: 'USask post-game Veo match analysis',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased font-serif">
        <ClientLayout>
          {children}
        </ClientLayout>
      </body>
    </html>
  );
}
