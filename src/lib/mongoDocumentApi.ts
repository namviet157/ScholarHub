import type { MongoDocumentPayload } from "@/types/scholar";

export async function fetchMongoDocument(
  mongoDocId: string | null | undefined
): Promise<MongoDocumentPayload | null> {
  if (!mongoDocId?.trim()) return null;

  const customBase = import.meta.env.VITE_DOCUMENT_CONTENTS_API_URL?.replace(/\/$/, "");
  const url = customBase
    ? `${customBase}/document/${encodeURIComponent(mongoDocId)}`
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
