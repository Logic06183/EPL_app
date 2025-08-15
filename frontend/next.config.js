/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // Temporarily using localhost - will update with Cloud Run URL
        destination: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/:path*',
      },
    ]
  },
}

module.exports = nextConfig