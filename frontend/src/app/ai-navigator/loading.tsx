import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import MainLayout from '@/components/layout/MainLayout';

export default function AINavigatorLoading() {
  return (
    <MainLayout>
      <div className="min-h-screen bg-gradient-to-br from-[#fff7ed] via-[#fff1f2] to-[#eff6ff] py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Hero banner skeleton */}
          <Skeleton variant="rectangular" width="100%" height={160} className="rounded-[28px] mb-10" />

          {/* Quick links grid */}
          <section className="mb-12">
            <div className="mb-5">
              <Skeleton variant="text" width={160} height={28} className="mb-2" />
              <Skeleton variant="text" width={280} height={16} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
              {[1, 2, 3, 4].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </section>

          {/* Section skeletons */}
          {[1, 2].map((s) => (
            <section key={s} className="mb-12">
              <Skeleton variant="rectangular" width="100%" height={80} className="rounded-2xl mb-6" />
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {[1, 2, 3].map((i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
