import type { Metadata } from 'next';
import { IBM_Plex_Mono, Public_Sans } from 'next/font/google';
import { ClientLayout } from './components/ClientLayout';
import '../styles/index.css';

// The same prebuilt image runs in live and test modes. Force runtime rendering
// so RTGS_MODE is not frozen to the value present during `next build`.
export const dynamic = 'force-dynamic';

const sans = Public_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-public-sans',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-data',
});

export const metadata: Metadata = {
  title: 'Game Analysis · USask Soccer',
  description: 'Live and post-game match intelligence for USask women’s soccer.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const configuredMode = process.env.RTGS_MODE;
  const mode = configuredMode === 'test' || configuredMode === 'replay'
    ? configuredMode
    : process.env.NODE_ENV === 'development' ? 'test' : 'live';
  return (
    <html lang="en" className="dark">
      <body className={`${sans.variable} ${mono.variable} min-h-screen bg-background text-foreground antialiased`}>
        <ClientLayout mode={mode}>
          {children}
        </ClientLayout>
      </body>
    </html>
  );
}
