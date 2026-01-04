# Multi-stage Dockerfile for Next.js Dashboard
#
# This Dockerfile uses a multi-stage build to create an optimized production image:
# 1. Base stage: Node.js 20 Alpine (lightweight base image)
# 2. Dependencies stage: Install npm dependencies
# 3. Builder stage: Build the Next.js application
# 4. Runner stage: Minimal production image with only necessary files
#
# The standalone output mode (configured in next.config.ts) creates a minimal
# production build that includes only the necessary files, significantly
# reducing the final image size.
#
# Security:
# - Runs as non-root user (nextjs:nodejs)
# - Minimal base image (Alpine Linux)
# - Only production dependencies in final image

FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variable for build
ENV NEXT_TELEMETRY_DISABLED 1

# Build Next.js app with standalone output
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
# The standalone output includes only necessary files
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port 3000 for Next.js server
EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Start the Next.js server
CMD ["node", "server.js"]

