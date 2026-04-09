'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Global error boundary caught an error:', error);
  }, [error]);

  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-bg flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-white rounded-3xl shadow-standard p-10 text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center mx-auto mb-6 text-2xl">
            !
          </div>
          <h1 className="text-2xl font-bold text-text-primary mb-3">站点暂时不可用</h1>
          <p className="text-text-secondary mb-8">
            我们已经捕获到这次异常。请稍后重试，或刷新页面后再继续。
          </p>
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center justify-center rounded-xl bg-primary px-5 py-3 text-white font-medium hover:opacity-90 transition-opacity"
          >
            重新加载
          </button>
        </div>
      </body>
    </html>
  );
}
