import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function DashboardLoading() {
  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* Header skeleton */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={32} height={32} />
            <div>
              <Skeleton variant="text" width={200} height={32} className="mb-1" />
              <Skeleton variant="text" width={300} height={16} />
            </div>
          </div>
          <Skeleton variant="rectangular" width={100} height={36} />
        </div>

        {/* Stats cards skeleton - 4 cols */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <Skeleton variant="text" width={80} height={16} className="mb-2" />
                  <Skeleton variant="text" width={100} height={32} />
                </div>
                <Skeleton variant="circular" width={48} height={48} />
              </div>
            </div>
          ))}
        </div>

        {/* Charts skeleton - 2 cols */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <SkeletonCard className="h-64" />
          <SkeletonCard className="h-64" />
        </div>

        {/* Ultra features skeleton - 3 cols */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <SkeletonCard key={i} className="h-48" />
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
