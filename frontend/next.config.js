/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // Using US region for now - will migrate to Africa region once deployed
        destination: process.env.NEXT_PUBLIC_API_URL || 'https://epl-backend-77913915885.us-central1.run.app/:path*',
      },
    ]
  },
}

module.exports = nextConfig