# Deploy ScholarHub on Railway

Use **two services** in one Railway project (same GitHub repo): **API** (Docker) and **Web** (Node static).

## 1. Service: API (FastAPI)

1. **New** → **GitHub Repo** → select this repository.
2. **Settings** → **Build**:
   - Builder: **Dockerfile**, path: **`Dockerfile.api`** (FastAPI image).
3. **Settings** → **Deploy**:
   - **Healthcheck path**: `/health`
   - **Healthcheck timeout**: `300` (first boot loads PyTorch + embeddings).
4. **Variables** (same names as `.env` on the server):

   | Variable | Notes |
   |----------|--------|
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_KEY` | **Service role** key (server-side) |
   | `OPENAI_API_KEY` | Required for `/chat/rag` |
   | `OPENAI_CHAT_MODEL` | Optional, default `gpt-4o-mini` |
   | `MONGO_URL` | Optional |
   | `DATABASE_NAME` | Optional (with Mongo) |
   | `DOCUMENT_CONTENTS_COLLECTION` | Optional |

   Railway injects **`PORT`** automatically; the image already uses it.

5. **Networking** → generate a public URL (e.g. `https://scholarhub-api.up.railway.app`).

## 2. Service: Web (Vite frontend)

1. **New** → **GitHub Repo** → **same repository** again.
2. **Settings** → **Build**:
   - **Option A — Docker**: Builder **Dockerfile**, path **`Dockerfile`** (root). Add **Docker Build Args** (same names as below) so Vite receives `VITE_*` at image build time.
   - **Option B — Nixpacks/Railpack**: If the platform defaults to the root Dockerfile, switch to **Railpack** / **Nixpacks** (Node). **Build**: `npm run build`. **Start**: `npm start` (`dist/` on `$PORT`).
3. **Variables** — set **before** the first build (Vite bakes `VITE_*` at build time):

   | Variable | Notes |
   |----------|--------|
   | `VITE_SUPABASE_URL` | Public Supabase URL |
   | `VITE_SUPABASE_ANON_KEY` | Anon key |
   | `VITE_SCHOLARHUB_API_URL` | Public URL of the **API** service (no trailing slash), e.g. `https://scholarhub-api.up.railway.app` |

4. **Networking** → public URL for the site.

## 3. After deploy

- Open the web URL; chat/search should call the API URL you set in `VITE_SCHOLARHUB_API_URL`.
- CORS: the API allows all origins by default; tighten in `server/scholarhub_api.py` if needed.

## 4. Optional: import / batch jobs

Use **`Dockerfile.import`** locally or as a separate one-off Railway service with command overridden to run your Python job (not the HTTP server).
