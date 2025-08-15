// next.config.js
var nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*"
      }
    ];
  }
};
module.exports = nextConfig;
