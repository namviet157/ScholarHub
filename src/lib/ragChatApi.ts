/** Shown when no arXiv ids or the API reports missing indexed chunks */
export const RAG_INSUFFICIENT_MESSAGE =
  "I don't have enough data to answer. Provide papers with an arXiv id and ensure chunk embeddings exist in Supabase (run the processing pipeline), or check MongoDB document content if using legacy ingest.";

const INSUFFICIENT_CLIENT = RAG_INSUFFICIENT_MESSAGE;

export type RagChatResult =
  | { ok: true; answer: string; citations: string[] }
  | { ok: false; code: string; message: string };

export async function ragChatQuery(params: {
  question: string;
  /** arXiv ids as stored in Supabase `papers.arxiv_id` / chunk `paper_id` */
  arxivIds: string[];
  paperTitles?: string[];
}): Promise<RagChatResult> {
  const ids = params.arxivIds
    .map((id) => String(id || "").trim())
    .filter((id) => id.length > 0);
  if (ids.length === 0) {
    return { ok: false, code: "INSUFFICIENT_DATA", message: INSUFFICIENT_CLIENT };
  }

  const base = import.meta.env.VITE_RAG_API_URL?.replace(/\/$/, "") ?? "";
  const url = base ? `${base}/chat/rag` : `/api/chat/rag`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: params.question,
        arxivIds: ids,
        paperTitles: params.paperTitles ?? [],
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
        "Could not reach the RAG API. In development, run `npm run api:documents` (Python/FastAPI) and ensure OPENAI_API_KEY plus Supabase env vars are set.",
    };
  }
}
