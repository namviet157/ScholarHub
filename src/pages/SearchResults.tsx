import { Filter, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import Header from "@/components/Header";
import SearchFilters from "@/components/SearchFilters";
import PaperCard from "@/components/PaperCard";
import { mockPapers } from "@/data/mockPapers";
import { useSearchParams } from "react-router-dom";

const SearchResults = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-1">
              {query ? `Results for "${query}"` : "Explore Papers"}
            </h1>
            <p className="text-muted">
              Found {mockPapers.length} papers
            </p>
          </div>

          {/* Mobile Filter Button */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" className="lg:hidden border-border">
                <SlidersHorizontal className="h-4 w-4 mr-2" />
                Filters
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 bg-card">
              <SheetHeader>
                <SheetTitle className="text-foreground">Filters</SheetTitle>
              </SheetHeader>
              <div className="mt-6">
                <SearchFilters />
              </div>
            </SheetContent>
          </Sheet>
        </div>

        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          <aside className="hidden lg:block w-64 shrink-0">
            <div className="sticky top-24 bg-card border border-border rounded-xl p-6">
              <div className="flex items-center gap-2 mb-6">
                <Filter className="h-5 w-5 text-primary" />
                <h2 className="font-semibold text-foreground">Filters</h2>
              </div>
              <SearchFilters />
            </div>
          </aside>

          {/* Results */}
          <main className="flex-1 space-y-4">
            {mockPapers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                highlightText={query}
              />
            ))}
          </main>
        </div>
      </div>
    </div>
  );
};

export default SearchResults;
