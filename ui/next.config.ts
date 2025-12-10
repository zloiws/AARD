import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  /* config options here */
  // Turbopack configuration for Next.js 16 (default bundler)
  turbopack: {},
  // Webpack config for --webpack flag compatibility
  webpack: (config, { isServer }) => {
    // Ensure dagre is properly handled
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      }
    }
    return config
  },
}

export default nextConfig
