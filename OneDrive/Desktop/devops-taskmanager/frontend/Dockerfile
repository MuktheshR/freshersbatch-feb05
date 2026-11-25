# syntax=docker/dockerfile:1

# ---------- Stage 1: build - Node toolchain compiles React into static files ----------
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# Commit package-lock.json so CI gets reproducible `npm ci` installs.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build

# ---------- Stage 2: runtime - only static assets + nginx, running as non-root ----------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
