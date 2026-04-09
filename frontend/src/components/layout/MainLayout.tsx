import { ReactNode } from 'react';
import Navigation from './Navigation';

interface MainLayoutProps {
  children: ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-bg">
      <Navigation />
      <main className="pt-[72px]">
        <div className="px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
