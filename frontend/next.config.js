/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  trailingSlash: true,
  distDir: 'out',
  images: {
    unoptimized: true
  },
  env: {
    // Default to production backend, can be overridden with env var
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app'
  },
  // Next.js 15 specific configurations
  experimental: {
    // Enable optimized package imports
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
}

module.exports = nextConfig
