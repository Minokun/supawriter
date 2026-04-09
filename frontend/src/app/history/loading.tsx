import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function HistoryLoading() {
  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header skeleton */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <Skeleton variant="circular" width={48} height={48} />
              <Skeleton variant="text" width={250} height={36} />
            </div>
            <Skeleton variant="text" width={400} height={20} />
          </div>
          <Skeleton variant="rectangular" width={120} height={40} />
        </div>

        {/* Stats section skeleton - 4 cols */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white/50 backdrop-blur-sm border border-border rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-4">
                <Skeleton variant="circular" width={48} height={48} />
                <div className="flex-1">
                  <Skeleton variant="text" width={80} height={16} className="mb-1" />
                  <Skeleton variant="text" width={60} height={24} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Search and filter skeleton */}
        <div className="bg-white border border-border rounded-2xl p-4 mb-8 flex flex-col md:flex-row gap-4">
          <Skeleton variant="rectangular" width="100%" height={48} />
          <div className="flex gap-3">
            <Skeleton variant="rectangular" width={120} height={40} />
            <Skeleton variant="rectangular" width={80} height={40} />
          </div>
        </div>

        {/* Article list skeleton */}
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-border rounded-2xl p-5 flex flex-col md:flex-row gap-6">
              <Skeleton variant="rectangular" width={64} height={64} />
              <div className="flex-1 min-w-0">
                <Skeleton variant="text" width={300} height={24} className="mb-2" />
                <div className="flex gap-4 mb-2">
                  <Skeleton variant="text" width={80} height={16} />
                  <Skeleton variant="text" width={60} height={16} />
                  <Skeleton variant="text" width={80} height={16} />
                </div>
              </div>
              <div className="flex gap-3 flex-shrink-0">
                {[1, 2, 3, 4].map((j) => (
                  <Skeleton key={j} variant="circular" width={44} height={44} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
