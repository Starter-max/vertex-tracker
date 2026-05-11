import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';

export const metadata: Metadata = {
  title: 'Mental Flow System',
  description: 'Capture, review, and sort incoming thoughts into active work, parking, and archive.',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'black-translucent', title: 'Mental Flow System' },
};

export const viewport = {
  themeColor: '#0f172a',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark">
      <body>
        {children}
        <Script id="mfs-sw" strategy="afterInteractive">{`if ('serviceWorker' in navigator) { window.addEventListener('load', () => navigator.serviceWorker.register('/service-worker.js').catch(() => {})); }`}</Script>
      </body>
    </html>
  );
}
