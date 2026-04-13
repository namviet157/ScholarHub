import type { MongoDocumentPayload } from "@/types/scholar";

function scholarhubApiBase(): string {
  return (
    import.meta.env.VITE_SCHOLARHUB_API_URL ||
    import.meta.env.VITE_RAG_API_URL ||
    ""
  ).replace(/\/$/, "");
}

export async function fetchMongoDocument(
  mongoDocId: string | null | undefined
): Promise<MongoDocumentPayload | null> {
  if (!mongoDocId?.trim()) return null;

  const base = scholarhubApiBase();
  const url = base
    ? `${base}/document/${encodeURIComponent(mongoDocId)}`
    : `/api/document/${encodeURIComponent(mongoDocId)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const data: unknown = await res.json();
    if (data == null || typeof data !== "object" || Array.isArray(data)) return null;
    return data as MongoDocumentPayload;
  } catch {
    return null;
  }
}
