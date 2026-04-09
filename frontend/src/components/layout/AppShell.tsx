'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Navigation from './Navigation';

interface AppShellProps {
  children: ReactNode;
}

const CHROME_HIDDEN_PREFIXES = ['/auth', '/login'];

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const showChrome = pathname ? !CHROME_HIDDEN_PREFIXES.some((prefix) => pathname.startsWith(prefix)) : true;

  if (!showChrome) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-bg">
      <Navigation />
      <main className="pt-[72px]">
        <div className="px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
