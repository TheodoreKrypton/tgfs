import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath: "/tgfs",
  assetPrefix: "/tgfs",
  images: {
    loader: "custom",
    loaderFile: "image-loader.js",
  },
};

export default nextConfig;
