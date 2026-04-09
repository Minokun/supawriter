import clsx from 'clsx';

interface LoadingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingDots({ className, size = 'md' }: LoadingDotsProps) {
  const sizeStyles = {
    sm: 'w-1 h-1',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  };

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      <span className={clsx(sizeStyles[size], 'bg-text-secondary rounded-full animate-dot-bounce')} style={{ animationDelay: '0ms' }} />
      <span className={clsx(sizeStyles[size], 'bg-text-secondary rounded-full animate-dot-bounce')} style={{ animationDelay: '160ms' }} />
      <span className={clsx(sizeStyles[size], 'bg-text-secondary rounded-full animate-dot-bounce')} style={{ animationDelay: '320ms' }} />
    </div>
  );
}

export default LoadingDots;
