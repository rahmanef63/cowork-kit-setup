// Purpose: Next.js (app router) configuration for the BYOK automation webapp.

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The Anthropic SDK is only ever imported from Convex server code (convex/),
  // never from the Next.js bundle, so no special webpack handling is required here.
};

export default nextConfig;
