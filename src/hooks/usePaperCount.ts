import { useQuery } from "@tanstack/react-query";
import { fetchPaperCount } from "@/lib/papersRepository";

export function usePaperCount() {
  return useQuery({
    queryKey: ["scholar", "paper-count"],
    queryFn: fetchPaperCount,
    staleTime: 120_000,
  });
}
