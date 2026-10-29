# The web page image: build the Next.js page, then run only the small
# "standalone" server it produces (next.config.mjs). Three stages, so the final
# image has no build tools and no source code.

# 1. Packages, exactly as in package-lock.json (reused while it doesn't change).
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# 2. Build. The API address is written into the page at build time: it is the
#    address the visitor's BROWSER calls, so localhost:8000, not the container name.
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# 3. Run, as the image's normal "node" user.
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node /app/.next/standalone ./
COPY --from=build --chown=node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
