import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function AIAssistantLoading() {
  return (
    <MainLayout>
      <div className="flex h-[calc(100vh-72px)] gap-6 px-4 py-4 max-w-[1600px] mx-auto">
        {/* Left sidebar skeleton */}
        <div className="w-80 flex-shrink-0">
          <div className="bg-surface border-2 border-border rounded-3xl p-6 h-full flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <Skeleton variant="circular" width={32} height={32} />
              <Skeleton variant="text" width={120} height={24} />
            </div>
            <Skeleton variant="rectangular" width="100%" height={40} className="mb-4 rounded-xl" />
            <div className="flex-1 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="p-3 rounded-xl">
                  <Skeleton variant="text" width="80%" height={16} className="mb-1" />
                  <Skeleton variant="text" width="50%" height={12} />
                </div>
              ))}
            </div>
            <div className="border-t border-border pt-3 mt-3">
              <Skeleton variant="text" width="60%" height={14} />
            </div>
          </div>
        </div>

        {/* Right main area skeleton */}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Skeleton variant="circular" width={64} height={64} className="mx-auto mb-4" />
            <Skeleton variant="text" width={200} height={24} className="mx-auto mb-2" />
            <Skeleton variant="text" width={300} height={16} className="mx-auto" />
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
