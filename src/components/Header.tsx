import { Search, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";

interface HeaderProps {
  showSearch?: boolean;
}

const Header = ({ showSearch = true }: HeaderProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(() => searchParams.get("q") ?? "");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isExplore = location.pathname === "/";

  useEffect(() => {
    if (isExplore) {
      setSearchQuery(searchParams.get("q") ?? "");
    }
  }, [isExplore, searchParams]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!isExplore) {
      if (q) navigate(`/?q=${encodeURIComponent(q)}`);
      return;
    }
    if (q) {
      setSearchParams({ q }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  };

  const handleQueryChange = (value: string) => {
    setSearchQuery(value);
    if (isExplore && !value.trim()) {
      setSearchParams({}, { replace: true });
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-lg">S</span>
          </div>
          <span className="font-semibold text-xl text-foreground hidden sm:block">ScholarHub</span>
        </Link>

        {showSearch && (
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-xl">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
              <Input
                type="search"
                placeholder="Search papers, topics, methods…"
                className="pl-10 bg-accent border-border focus-visible:ring-primary"
                value={searchQuery}
                onChange={(e) => handleQueryChange(e.target.value)}
              />
            </div>
          </form>
        )}

        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-card p-4 space-y-4">
          {showSearch && (
            <form onSubmit={handleSearch}>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                <Input
                  type="search"
                  placeholder="Semantic search…"
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => handleQueryChange(e.target.value)}
                />
              </div>
            </form>
          )}
          <nav className="flex flex-col gap-2">
            <Button variant="ghost" asChild className="justify-start">
              <Link to="/" onClick={() => setMobileMenuOpen(false)}>
                Explore
              </Link>
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
