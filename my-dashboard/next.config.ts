/**
 * Next.js Configuration
 * 
 * This file configures the Next.js application for production deployment.
 * 
 * Key Configuration:
 * - output: 'standalone' - Enables standalone output mode for Docker deployments.
 *   This creates a minimal production build that includes only necessary files.
 * 
 * Optional Features (commented out):
 * - API rewrites: Can be enabled to proxy API calls through Next.js server.
 *   This is not needed when using the API route proxy (/app/api/coding-agent/query/route.ts).
 * 
 * Environment Variables:
 * - NEXT_PUBLIC_API_URL: Public API URL (not used, we use API route proxy)
 * - BACKEND_URL: Backend URL for API route proxy (server-side only)
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployments
  // This creates a minimal production build optimized for containerization
  output: 'standalone',
  
  /* config options here */
  
  // Optional: Rewrite API calls to backend
  // Uncomment if you want to proxy API calls through Next.js
  // Note: We use API routes instead (app/api/coding-agent/query/route.ts)
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
