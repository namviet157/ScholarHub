import { useQuery } from "@tanstack/react-query";
import { fetchPaperByIdFromSupabase } from "@/lib/papersRepository";
import { mergeMongoIntoPaper, paperFromSupabaseOnly } from "@/lib/scholarPaperMappers";
import { fetchMongoDocument } from "@/lib/mongoDocumentApi";
import type { MongoDocumentPayload, Paper } from "@/types/scholar";

function hasRagChunks(mongo: MongoDocumentPayload | null): boolean {
  if (!mongo || !Array.isArray(mongo.chunks)) return false;
  return mongo.chunks.some((c) => String(c.text || "").trim().length > 15);
}

export type ScholarPaperDetail = {
  paper: Paper;
  mongoAvailable: boolean;
};

export function useScholarPaperDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["scholar", "paper", id],
    enabled: Boolean(id),
    queryFn: async (): Promise<ScholarPaperDetail | null> => {
      const row = await fetchPaperByIdFromSupabase(id!);
      if (!row) return null;
      const base = paperFromSupabaseOnly(row);
      const mongo = row.mongo_doc_id ? await fetchMongoDocument(row.mongo_doc_id) : null;
      const paper = mergeMongoIntoPaper(base, mongo);
      const mongoAvailable = hasRagChunks(mongo);
      return { paper, mongoAvailable };
    },
    staleTime: 120_000,
  });
}
