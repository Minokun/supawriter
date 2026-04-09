import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function HotspotsLoading() {
  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* Header skeleton */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={32} height={32} />
            <div>
              <Skeleton variant="text" width={120} height={32} className="mb-1" />
              <Skeleton variant="text" width={300} height={16} />
            </div>
          </div>
          <div className="flex gap-2">
            <Skeleton variant="rectangular" width={100} height={40} />
            <Skeleton variant="rectangular" width={100} height={40} />
            <Skeleton variant="rectangular" width={100} height={40} />
          </div>
        </div>

        {/* Status cards skeleton - 4 cols */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-xl p-4">
              <div className="flex items-center gap-3">
                <Skeleton variant="circular" width={40} height={40} />
                <div className="flex-1">
                  <Skeleton variant="text" width={60} height={14} className="mb-1" />
                  <Skeleton variant="text" width={80} height={20} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Platform tabs skeleton */}
        <div className="flex gap-2 mb-6 overflow-hidden">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="rectangular" width={100} height={40} />
          ))}
        </div>

        {/* Hotspots list skeleton */}
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-3 p-3 border-b border-border last:border-b-0">
              <Skeleton variant="circular" width={32} height={32} />
              <Skeleton variant="rectangular" width={60} height={24} />
              <div className="flex-1 min-w-0">
                <Skeleton variant="text" width={400} height={16} className="mb-1" />
                <Skeleton variant="text" width={200} height={12} />
              </div>
              <Skeleton variant="rectangular" width={80} height={32} />
            </div>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
