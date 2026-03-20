import type { Metadata } from 'next';
import { Navigation } from './components/Navigation';
import '../styles/index.css';

export const metadata: Metadata = {
  title: 'RTGS Coach Dashboard',
  description: 'Real-time tactical insights and player performance',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased font-serif">
        <Navigation />
        <main className="flex-1 p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
