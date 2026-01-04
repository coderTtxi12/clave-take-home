import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Removed 'standalone' output - Vercel handles this automatically
  // output: 'standalone', // Only needed for Docker deployments
  
  /* config options here */
  
  // Optional: Rewrite API calls to backend
  // Uncomment if you want to proxy API calls through Next.js
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: `${process.env.API_BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
  //     },
  //   ];
  // },
};

export default nextConfig;
