import { Filter, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import Header from "@/components/Header";
import SearchFilters from "@/components/SearchFilters";
import PaperCard from "@/components/PaperCard";
import { useSearchParams } from "react-router-dom";
import { useScholarPapers } from "@/hooks/useScholarPapers";
import {
  applyPaperFilters,
  orderPapersBySemanticThenLexical,
  type PaperListFilters,
} from "@/lib/papersRepository";
import { semanticSearchPapers } from "@/lib/semanticSearchApi";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

const currentYear = new Date().getFullYear();
const PAGE_SIZE = 10;

function buildDefaultFilters(papers: { year: number }[]): PaperListFilters {
  if (!papers.length) {
    return { yearMin: 2000, yearMax: currentYear, venues: [], categories: [] };
  }
  let mn = Infinity;
  let mx = -Infinity;
  for (const p of papers) {
    mn = Math.min(mn, p.year);
    mx = Math.max(mx, p.year);
  }
  return {
    yearMin: Number.isFinite(mn) ? mn : 2000,
    yearMax: Number.isFinite(mx) ? mx : currentYear,
    venues: [],
    categories: [],
  };
}

const Explore = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const { data: papers = [], isLoading, isError, error } = useScholarPapers();
  const [filters, setFilters] = useState<PaperListFilters>(() => ({
    yearMin: 2000,
    yearMax: currentYear,
    venues: [],
    categories: [],
  }));
  const [page, setPage] = useState(1);

  const { data: semanticData, isFetching: semanticFetching } = useQuery({
    queryKey: ["semantic-search", query],
    queryFn: () => semanticSearchPapers(query),
    enabled: Boolean(query.trim()) && !isLoading,
    staleTime: 45_000,
  });

  useEffect(() => {
    if (!papers.length) return;
    setFilters((prev) => {
      const d = buildDefaultFilters(papers);
      return {
        ...prev,
        yearMin: Math.min(prev.yearMin, d.yearMin),
        yearMax: Math.max(prev.yearMax, d.yearMax),
      };
    });
  }, [papers]);

  useEffect(() => {
    setPage(1);
  }, [query, filters, papers.length]);

  const venueOptions = useMemo(() => {
    const s = new Set<string>();
    papers.forEach((p) => {
      if (p.venue?.trim()) s.add(p.venue.trim());
    });
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [papers]);

  const categoryOptions = useMemo(() => {
    const s = new Set<string>();
    papers.forEach((p) => {
      (p.categories ?? []).forEach((c) => {
        if (c?.trim()) s.add(c.trim());
      });
    });
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [papers]);

  const preFiltered = useMemo(() => {
    const semanticWorked = Boolean(
      query.trim() && semanticData?.ok && semanticData.arxivIds.length > 0
    );
    return orderPapersBySemanticThenLexical(
      papers,
      query,
      semanticData?.arxivIds,
      semanticWorked
    );
  }, [papers, query, semanticData]);

  const filtered = useMemo(
    () => applyPaperFilters(preFiltered, filters),
    [preFiltered, filters]
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, safePage]);

  const filterPanel = (
    <SearchFilters
      value={filters}
      onChange={setFilters}
      venueOptions={venueOptions}
      categoryOptions={categoryOptions}
    />
  );

  const rangeStart = filtered.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(safePage * PAGE_SIZE, filtered.length);

  const statusLine = (() => {
    if (isLoading) return "Loading…";
    if (isError) return error instanceof Error ? error.message : "Could not load papers";
    if (query.trim() && semanticFetching) return "Ranking with embeddings (semantic)…";
    if (query.trim() && semanticData?.ok === false && semanticData.message) {
      return `Semantic search unavailable — using keywords. (${semanticData.message.slice(0, 120)}${semanticData.message.length > 120 ? "…" : ""})`;
    }
    if (filtered.length === 0) {
      return `0 matches`;
    }
    return `Showing ${rangeStart}–${rangeEnd} of ${filtered.length} papers`;
  })();

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-1">
              {query ? `Results for "${query}"` : "Explore Papers"}
            </h1>
            <p className="text-muted text-sm sm:text-base">{statusLine}</p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-muted"
              onClick={() => setFilters(buildDefaultFilters(papers))}
            >
              Reset filters
            </Button>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" className="lg:hidden border-border">
                  <SlidersHorizontal className="h-4 w-4 mr-2" />
                  Filters
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-80 bg-card overflow-y-auto">
                <SheetHeader>
                  <SheetTitle className="text-foreground">Filters</SheetTitle>
                </SheetHeader>
                <div className="mt-6">{filterPanel}</div>
              </SheetContent>
            </Sheet>
          </div>
        </div>

        <div className="flex gap-8">
          <aside className="hidden lg:block w-64 shrink-0">
            <div className="sticky top-24 bg-card border border-border rounded-xl p-6 max-h-[calc(100vh-8rem)] overflow-y-auto">
              <div className="flex items-center gap-2 mb-6">
                <Filter className="h-5 w-5 text-primary" />
                <h2 className="font-semibold text-foreground">Filters</h2>
              </div>
              {filterPanel}
            </div>
          </aside>

          <main className="flex-1 space-y-4">
            {isLoading && <p className="text-sm text-muted">Loading papers…</p>}
            {!isLoading && !isError && filtered.length === 0 && (
              <p className="text-sm text-muted">No papers match your search and filters.</p>
            )}
            {!isLoading &&
              !isError &&
              paginated.map((paper) => (
                <PaperCard key={paper.id} paper={paper} highlightText={query} />
              ))}

            {!isLoading && !isError && totalPages > 1 && (
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6 border-t border-border">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    disabled={safePage <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted tabular-nums px-2">
                    Page {safePage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    disabled={safePage >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default Explore;
