import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone：产出自包含 server.js，供 Docker 运行阶段最小化拷贝
  output: "standalone",
  // 隐藏开发工具悬浮按钮（不属于产品设计稿）
  devIndicators: false,
  // 后端 FastAPI(8000)：/api 代理转发（与原 Vite server.proxy 等价，SSE 流式透传）
  async rewrites() {
    const api = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};

export default nextConfig;
