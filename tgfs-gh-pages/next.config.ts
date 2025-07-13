import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: '/tgfs',
  assetPrefix: '/tgfs',
  images: {
    unoptimized: true
  }
};

export default nextConfig;
