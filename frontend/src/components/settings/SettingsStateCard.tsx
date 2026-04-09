'use client';

import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { Loader2 } from 'lucide-react';

interface SettingsStateCardProps {
  mode: 'auth' | 'loading';
  authMessage?: string;
  signinHref?: string;
  statusText?: string;
}

export function SettingsStateCard({
  mode,
  authMessage,
  signinHref = '/auth/signin',
  statusText,
}: SettingsStateCardProps) {
  if (mode === 'auth') {
    return (
      <Card padding="xl">
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-text-secondary text-lg mb-4">
            {authMessage || '请先登录以访问系统设置'}
          </p>
          <Button variant="primary" onClick={() => window.location.href = signinHref}>
            前往登录
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="xl">
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="animate-spin text-primary mb-4" size={48} />
        <p className="text-text-secondary">{statusText || '加载中...'}</p>
      </div>
    </Card>
  );
}
