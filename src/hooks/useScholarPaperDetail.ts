import { useQuery } from "@tanstack/react-query";
import { fetchPaperByIdFromSupabase } from "@/lib/papersRepository";
import { mergeMongoIntoPaper, paperFromSupabaseOnly } from "@/lib/scholarPaperMappers";
import { fetchMongoDocument } from "@/lib/mongoDocumentApi";

export function useScholarPaperDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["scholar", "paper", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const row = await fetchPaperByIdFromSupabase(id!);
      if (!row) return null;
      const base = paperFromSupabaseOnly(row);
      const mongo = row.mongo_doc_id ? await fetchMongoDocument(row.mongo_doc_id) : null;
      return mergeMongoIntoPaper(base, mongo);
    },
    staleTime: 120_000,
  });
}
