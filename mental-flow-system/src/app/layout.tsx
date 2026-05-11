import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Mental Flow System',
  description: 'Capture, review, and sort incoming thoughts into active work, parking, and archive.',
  manifest: '/manifest.json',
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
      <body>{children}</body>
    </html>
  );
}
