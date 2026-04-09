import { ReactNode } from 'react';
import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  className,
  variant = 'text',
  width,
  height,
  animation = 'wave',
}: SkeletonProps) {
  const baseStyles = 'bg-bg rounded';

  const variantStyles = {
    text: 'rounded-md h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
  };

  const animationStyles = {
    pulse: 'animate-pulse',
    wave: 'relative overflow-hidden',
    none: '',
  };

  const waveGradient = (
    <span className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite]">
      <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent" />
    </span>
  );

  return (
    <div
      className={clsx(
        baseStyles,
        variantStyles[variant],
        animationStyles[animation],
        animation === 'wave' && 'relative overflow-hidden',
        className
      )}
      style={{ width, height }}
    >
      {animation === 'wave' && waveGradient}
    </div>
  );
}

interface SkeletonCardProps {
  children?: ReactNode;
  className?: string;
}

export function SkeletonCard({ children, className }: SkeletonCardProps) {
  return (
    <div className={clsx('bg-surface border-2 border-border rounded-3xl p-8', className)}>
      {children || (
        <>
          <Skeleton variant="text" width="60%" height={24} className="mb-4" />
          <Skeleton variant="text" className="mb-2" />
          <Skeleton variant="text" width="80%" className="mb-4" />
          <div className="flex gap-2">
            <Skeleton variant="rectangular" width={60} height={24} />
            <Skeleton variant="rectangular" width={60} height={24} />
          </div>
        </>
      )}
    </div>
  );
}

export default Skeleton;
