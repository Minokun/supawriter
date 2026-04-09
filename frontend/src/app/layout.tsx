import type { Metadata } from 'next';
import './globals.css';
import AuthProvider from '@/components/AuthProvider';
import { AuthContextProvider } from '@/contexts/AuthContext';
import { ModelConfigProvider } from '@/contexts/ModelConfigContext';
import { ToastProvider } from '@/components/ui/ToastContainer';
import PageProgress from '@/components/ui/PageProgress';
import { Suspense } from 'react';

export const metadata: Metadata = {
  title: '超能写 - AI智能写作平台',
  description: '文章创作、推文选题、内容再创作 - 一键生成高质量内容',
};

/**
 * 全局加载组件 - Suspense fallback
 * 提供一致的加载体验，防止布局抖动
 */
function GlobalLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-border border-t-primary rounded-full animate-spin"></div>
        </div>
        <p className="text-sm text-text-secondary font-medium">加载中...</p>
      </div>
    </div>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider>
          <AuthContextProvider>
            <ModelConfigProvider>
              <ToastProvider>
                <Suspense fallback={null}>
                  <PageProgress />
                </Suspense>
                {/* Suspense boundary 启用渐进式渲染 */}
                <Suspense fallback={<GlobalLoading />}>
                  {children}
                </Suspense>
              </ToastProvider>
            </ModelConfigProvider>
          </AuthContextProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
