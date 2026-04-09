'use client';

import { useEffect } from 'react';
import Button from '@/components/ui/Button';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Route error boundary caught an error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-6">
      <div className="max-w-lg w-full bg-white rounded-3xl shadow-standard p-10 text-center">
        <div className="w-16 h-16 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center mx-auto mb-6 text-2xl">
          !
        </div>
        <h1 className="text-2xl font-bold text-text-primary mb-3">页面暂时出了点问题</h1>
        <p className="text-text-secondary mb-8">
          请稍后重试；如果问题持续存在，可以先返回首页或重新进入当前功能页。
        </p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="secondary" onClick={() => window.location.assign('/')}>
            返回首页
          </Button>
          <Button variant="primary" onClick={reset}>
            重新加载
          </Button>
        </div>
      </div>
    </div>
  );
}
