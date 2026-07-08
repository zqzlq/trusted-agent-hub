import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Trusted Agent Hub',
  description: 'Discover and install trusted AI agent capability packages',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="header-inner">
            <a href="/" className="header-logo">
              Trusted <span>Agent Hub</span>
            </a>
            <nav className="header-nav">
              <a href="/">Browse</a>
            </nav>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
