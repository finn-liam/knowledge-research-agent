# Next.js standalone 部署：三阶段构建，运行层只带自包含产物（~200MB 级）
# 构建阶段
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 运行阶段：standalone server（含 server.js 与精简 node_modules）
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
# 容器内默认指向 compose 网络中的 api 服务（本地裸跑默认 127.0.0.1:8000）
ENV API_PROXY_TARGET=http://api:8000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
