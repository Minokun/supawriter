import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function WriterLoading() {
  return (
    <MainLayout>
      <div className="max-w-[1400px] mx-auto">
        {/* Header skeleton */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Skeleton variant="circular" width={28} height={28} />
            <Skeleton variant="text" width={150} height={28} />
          </div>
          <Skeleton variant="text" width={300} height={16} />
        </div>

        {/* Form and queue skeleton - 2 cols */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Writer form skeleton */}
          <div className="bg-white rounded-3xl p-8 shadow-standard">
            <div className="space-y-6">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i}>
                  <Skeleton variant="text" width={100} height={16} className="mb-2" />
                  {i === 3 ? (
                    <Skeleton variant="rectangular" width="100%" height={120} />
                  ) : (
                    <Skeleton variant="rectangular" width="100%" height={48} />
                  )}
                </div>
              ))}
              <Skeleton variant="rectangular" width="100%" height={48} />
            </div>
          </div>

          {/* Task queue skeleton */}
          <div className="bg-surface border-2 border-border rounded-3xl p-6">
            <div className="flex items-center justify-between mb-6">
              <Skeleton variant="text" width={120} height={20} />
              <Skeleton variant="circular" width={32} height={32} />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white border border-border rounded-xl p-4 mb-4 last:mb-0">
                <div className="flex items-start gap-4">
                  <Skeleton variant="circular" width={40} height={40} />
                  <div className="flex-1 min-w-0">
                    <Skeleton variant="text" width={200} height={18} className="mb-2" />
                    <Skeleton variant="text" width="60%" height={14} className="mb-3" />
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                      <Skeleton variant="rectangular" width="40%" height={8} className="h-2" />
                    </div>
                    <div className="flex gap-2">
                      <Skeleton variant="rectangular" width={60} height={24} />
                      <Skeleton variant="rectangular" width={60} height={24} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
