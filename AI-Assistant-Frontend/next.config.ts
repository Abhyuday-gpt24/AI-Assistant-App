import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the EC2 host to load dev resources (HMR, JS chunks) when running `next dev`.
  // Without this, Next.js blocks /_next/* from this origin and the page never hydrates.
  allowedDevOrigins: ["100.48.47.97"],
};

export default nextConfig;
