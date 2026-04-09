import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function SettingsLoading() {
  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto">
        {/* Header skeleton */}
        <div className="flex items-center gap-3 mb-8">
          <Skeleton variant="circular" width={32} height={32} />
          <div>
            <Skeleton variant="text" width={120} height={32} className="mb-1" />
            <Skeleton variant="text" width={200} height={16} />
          </div>
        </div>

        {/* Settings sections skeleton */}
        <div className="space-y-6">
          {/* Membership card skeleton */}
          <div className="bg-gradient-to-br from-primary/5 to-purple-500/5 border-2 border-dashed border-primary/30 rounded-3xl p-8">
            <div className="flex items-center gap-6">
              <Skeleton variant="circular" width={64} height={64} />
              <div className="flex-1">
                <Skeleton variant="text" width={200} height={28} className="mb-2" />
                <Skeleton variant="text" width={300} height={16} />
              </div>
              <Skeleton variant="rectangular" width={140} height={40} />
            </div>
          </div>

          {/* Settings cards skeleton */}
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <Skeleton variant="circular" width={24} height={24} />
                  <Skeleton variant="text" width={150} height={20} />
                </div>
                <Skeleton variant="circular" width={32} height={32} />
              </div>
              {[1, 2, 3].map((j) => (
                <div key={j} className="flex items-center justify-between py-4 border-b border-border last:border-b-0">
                  <div>
                    <Skeleton variant="text" width={180} height={16} className="mb-2" />
                    <Skeleton variant="text" width={300} height={14} />
                  </div>
                  <Skeleton variant="rectangular" width={48} height={28} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
