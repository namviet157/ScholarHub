export const RAG_INSUFFICIENT_MESSAGE =
  "I don't have enough data to answer. Please try again with a different paper.";

const INSUFFICIENT_CLIENT = RAG_INSUFFICIENT_MESSAGE;

const MONGO_ID_RE = /^[a-f0-9]{24}$/i;

export type RagChatResult =
  | { ok: true; answer: string; citations: string[] }
  | { ok: false; code: string; message: string };

export async function ragChatQuery(params: {
  question: string;
  arxivIds: string[];
  paperTitles?: string[];
  /** MongoDB ObjectId strings for fallback when pgvector chunks are missing. */
  mongoDocIds?: string[];
}): Promise<RagChatResult> {
  const ids = params.arxivIds
    .map((id) => String(id || "").trim())
    .filter((id) => id.length > 0);
  const mongoIds = (params.mongoDocIds ?? [])
    .map((id) => String(id || "").trim())
    .filter((id) => MONGO_ID_RE.test(id));

  if (ids.length === 0 && mongoIds.length === 0) {
    return { ok: false, code: "INSUFFICIENT_DATA", message: INSUFFICIENT_CLIENT };
  }

  const base = (
    import.meta.env.VITE_SCHOLARHUB_API_URL ||
    import.meta.env.VITE_RAG_API_URL ||
    ""
  ).replace(/\/$/, "");
  const url = base ? `${base}/chat/rag` : `/api/chat/rag`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: params.question,
        arxivIds: ids,
        paperTitles: params.paperTitles ?? [],
        mongoDocIds: mongoIds,
      }),
    });

    const data = (await res.json()) as Record<string, unknown>;

    if (!res.ok) {
      const msg = typeof data.message === "string" ? data.message : `Request failed (${res.status})`;
      return { ok: false, code: String(data.code || "ERROR"), message: msg };
    }

    if (data.ok === false) {
      return {
        ok: false,
        code: String(data.code || "INSUFFICIENT_DATA"),
        message: typeof data.message === "string" ? data.message : INSUFFICIENT_CLIENT,
      };
    }

    const answer = typeof data.answer === "string" ? data.answer : "";
    const citations = Array.isArray(data.citations) ? data.citations.map(String) : [];
    return { ok: true, answer, citations };
  } catch {
    return {
      ok: false,
      code: "NETWORK",
      message:
        "Could not reach the RAG API. In development, run `npm run api` (Python/FastAPI) and ensure OPENAI_API_KEY plus Supabase env vars are set.",
    };
  }
}
