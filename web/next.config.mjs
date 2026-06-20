/** @type {import('next').NextConfig} */

// On GitHub Pages the site is served from a subpath (/apple-health-data), so the
// Pages build sets PAGES_BASE_PATH to prefix asset/route URLs. Local dev and any
// root-domain host (Cloudflare/Vercel) leave it unset and serve from "/".
const basePath = process.env.PAGES_BASE_PATH || "";

const nextConfig = {
  // Static export — the whole app is pre-rendered to HTML/JS at build time and
  // can be served from any static host (GitHub Pages, Netlify, S3, …).
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
