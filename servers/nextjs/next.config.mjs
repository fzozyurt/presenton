const nextConfig = {
  reactStrictMode: false,
  distDir: ".next-build",
  output: "standalone",

  // In dev mode, allow connections from localhost for HMR.
  ...(process.env.NODE_ENV !== "production"
    ? {
        allowedDevOrigins: [
          "http://127.0.0.1:40001",
          "http://localhost:40001",
          "127.0.0.1",
          "localhost",
        ],
      }
    : {}),

  // Rewrites: proxy /api/v1/* and /app_data/* to FastAPI backend.
  // In Docker/nginx this is handled by nginx.conf; for local dev (no nginx)
  // Next.js proxies directly to the FastAPI port.
  async rewrites() {
    const fastApiBase =
      process.env.NEXT_PUBLIC_FAST_API ||
      process.env.FAST_API_INTERNAL_URL ||
      "http://127.0.0.1:8000";

    return [
      {
        source: "/api/v1/:path*",
        destination: `${fastApiBase}/api/v1/:path*`,
      },
      {
        source: "/app_data/:path*",
        destination: `${fastApiBase}/app_data/:path*`,
      },
    ];
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "pub-7c765f3726084c52bcd5d180d51f1255.r2.dev",
      },
      {
        protocol: "https",
        hostname: "pptgen-public.ap-south-1.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "pptgen-public.s3.ap-south-1.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "img.icons8.com",
      },
      {
        protocol: "https",
        hostname: "present-for-me.s3.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "yefhrkuqbjcblofdcpnr.supabase.co",
      },
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
      {
        protocol: "https",
        hostname: "picsum.photos",
      },
      {
        protocol: "https",
        hostname: "unsplash.com",
      },
    ],
  },
  
};

export default nextConfig;
