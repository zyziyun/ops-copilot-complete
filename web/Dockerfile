# --- builder ---
FROM node:20-slim AS builder
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# baked into the client bundle; browser hits the API from the host
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# --- runner: Next.js standalone output ---
FROM node:20-slim AS runner
WORKDIR /web
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=builder /web/public ./public
COPY --from=builder /web/.next/standalone ./
COPY --from=builder /web/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
