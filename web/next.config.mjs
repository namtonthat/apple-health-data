/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — the whole app is pre-rendered to HTML/JS at build time and
  // can be served from any static host (Vercel, Netlify, S3, GitHub Pages).
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
