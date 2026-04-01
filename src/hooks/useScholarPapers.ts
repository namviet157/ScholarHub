import { useQuery } from "@tanstack/react-query";
import { fetchPapersFromSupabase } from "@/lib/papersRepository";

export function useScholarPapers() {
  return useQuery({
    queryKey: ["scholar", "papers"],
    queryFn: () => fetchPapersFromSupabase(500),
    staleTime: 60_000,
  });
}
