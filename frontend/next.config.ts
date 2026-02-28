import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
      },
      {
        source: "/ws",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/ws`,
      },
    ];
  },
};

export default nextConfig;
