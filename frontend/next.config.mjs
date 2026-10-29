// Next.js settings for the bgchange web page.
//
// output "standalone" makes `next build` produce a small self-contained server
// (used by the Docker image in step 10).

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
