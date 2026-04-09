import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function BatchLoading() {
  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* Header skeleton */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={32} height={32} />
            <div>
              <Skeleton variant="text" width={150} height={32} className="mb-1" />
              <Skeleton variant="text" width={250} height={16} />
            </div>
          </div>
          <Skeleton variant="rectangular" width={140} height={40} />
        </div>

        {/* Empty state skeleton */}
        <div className="bg-surface border border-border rounded-3xl p-16 text-center">
          <Skeleton variant="circular" width={64} height={64} className="mx-auto mb-4" />
          <Skeleton variant="text" width={200} height={24} className="mx-auto mb-2" />
          <Skeleton variant="text" width={300} height={16} className="mx-auto mb-6" />
          <Skeleton variant="rectangular" width={160} height={40} className="mx-auto" />
        </div>
      </div>
    </MainLayout>
  );
}
