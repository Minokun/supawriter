/** @type {import('next').NextConfig} */
const backendOrigin = (process.env.INTERNAL_API_URL || 'http://localhost:8000')
  .replace(/\/+$/, '')
  .replace(/\/api$/, '');

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: [],
  },
  // 延长 HMR 页面在内存中的保留时间，减少 CSS chunk 被回收后 404 的概率
  onDemandEntries: {
    maxInactiveAge: 60 * 60 * 1000,   // 1 小时
    pagesBufferLength: 10,
  },
  webpack: (config, { dev }) => {
    if (dev) {
      // 开发模式下禁用 filesystem 持久缓存，避免旧 CSS chunk hash 残留
      config.cache = {
        type: 'memory',
      };
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${backendOrigin}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
