/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  /** Optional origin of FastAPI (scholarhub_api). Dev default: Vite proxy `/api`. */
  readonly VITE_SCHOLARHUB_API_URL?: string;
  readonly VITE_RAG_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
