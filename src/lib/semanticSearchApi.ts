function apiBase(): string {
  return (
    import.meta.env.VITE_SCHOLARHUB_API_URL ||
    import.meta.env.VITE_RAG_API_URL ||
    ""
  ).replace(/\/$/, "");
}

export type SemanticSearchResponse = {
  ok: boolean;
  arxivIds: string[];
  scores: number[];
  message?: string;
};

export async function semanticSearchPapers(query: string, limit = 64): Promise<SemanticSearchResponse> {
  const q = query.trim();
  if (!q) {
    return { ok: true, arxivIds: [], scores: [] };
  }

  const base = apiBase();
  const url = base ? `${base}/search/semantic` : `/api/search/semantic`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, limit }),
    });
    const data = (await res.json()) as Record<string, unknown>;

    if (!res.ok) {
      return {
        ok: false,
        arxivIds: [],
        scores: [],
        message: typeof data.message === "string" ? data.message : `Request failed (${res.status})`,
      };
    }

    const arxivIds = Array.isArray(data.arxivIds) ? data.arxivIds.map(String) : [];
    const scores = Array.isArray(data.scores) ? data.scores.map((x) => Number(x)) : [];
    return { ok: data.ok !== false, arxivIds, scores };
  } catch {
    return {
      ok: false,
      arxivIds: [],
      scores: [],
      message: "Could not reach the search API. Run `npm run api` with Supabase credentials and paper embeddings.",
    };
  }
}
