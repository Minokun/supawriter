import { ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps {
  children: ReactNode;
  className?: string;
  hoverable?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'xl';
}

export default function Card({
  children,
  className,
  hoverable = false,
  padding = 'xl',
}: CardProps) {
  const paddingStyles = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-8',
  };

  return (
    <div
      className={clsx(
        // 基础样式
        'bg-surface border-2 border-border rounded-3xl shadow-light',
        // 统一过渡效果
        'transition-all duration-200 ease-out',
        paddingStyles[padding],
        // Hover 效果：缩放 + 阴影 + 边框颜色
        hoverable && 'hover:scale-[1.02] hover:shadow-standard hover:border-[#FCA5A5] cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
}
