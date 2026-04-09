'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

interface PageProgressProps {
  color?: string;
  height?: string;
}

export function PageProgress({ color = 'bg-primary', height = 'h-1' }: PageProgressProps) {
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const hasMountedRef = useRef(false);

  useEffect(() => {
    // Skip the first render so the home page doesn't fake a loading bar on initial load.
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      return;
    }

    setLoading(true);
    setProgress(0);

    // Keep route transitions feeling responsive instead of forcing a long 2.6s loading bar.
    const timers = [
      setTimeout(() => setProgress(35), 50),
      setTimeout(() => setProgress(70), 180),
      setTimeout(() => setProgress(90), 320),
      setTimeout(() => setProgress(100), 500),
      setTimeout(() => setLoading(false), 620),
    ];

    return () => {
      timers.forEach(t => clearTimeout(t));
    };
  }, [pathname, searchParams]);

  if (!loading) return null;

  return (
    <div className={`fixed top-0 left-0 right-0 z-[100] ${height} bg-bg`}>
      <div
        className={`h-full ${color} transition-all duration-300 ease-out`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

export default PageProgress;
