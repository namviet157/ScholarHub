# ScholarHub Vite + React frontend (static build, served with `serve`)
# Build-time: pass Railway/build args for Vite (baked into the bundle).
# VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_SCHOLARHUB_API_URL (optional: VITE_RAG_API_URL)
# Runtime: Railway sets PORT; `npm start` serves ./dist.

FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json \
 postcss.config.js tailwind.config.ts components.json ./
COPY src ./src
COPY public ./public

ARG VITE_SUPABASE_URL=
ARG VITE_SUPABASE_ANON_KEY=
ARG VITE_SCHOLARHUB_API_URL=
ARG VITE_RAG_API_URL=

ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
    VITE_SCHOLARHUB_API_URL=$VITE_SCHOLARHUB_API_URL \
    VITE_RAG_API_URL=$VITE_RAG_API_URL

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/dist ./dist
COPY scripts/static-serve.mjs ./scripts/static-serve.mjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||'3000')+'/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm", "start"]
