/** @type {import('next').NextConfig} */
const nextConfig = {
  // three/examples の ESM をそのままバンドルする
  transpilePackages: ['three'],
};

export default nextConfig;
