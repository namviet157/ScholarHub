import { Search, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface HeaderProps {
  showSearch?: boolean;
}

const Header = ({ showSearch = true }: HeaderProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { user, profile, signOut } = useAuth();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-lg">S</span>
          </div>
          <span className="font-semibold text-xl text-foreground hidden sm:block">ScholarHub</span>
        </Link>

        {/* Search Bar - Desktop */}
        {showSearch && (
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-xl">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
              <Input
                type="search"
                placeholder="Search papers, authors, topics..."
                className="pl-10 bg-accent border-border focus-visible:ring-primary"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </form>
        )}

        {/* Navigation - Desktop */}
        <nav className="hidden md:flex items-center gap-2">
          <Button variant="ghost" asChild className="text-foreground hover:text-primary hover:bg-accent">
            <Link to="/search">Explore</Link>
          </Button>
          <Button variant="ghost" asChild className="text-foreground hover:text-primary hover:bg-accent">
            <Link to="/chat">Ask AI</Link>
          </Button>
          <Button variant="ghost" asChild className="text-foreground hover:text-primary hover:bg-accent">
            <Link to="/dashboard">Dashboard</Link>
          </Button>
          <div className="w-px h-6 bg-border mx-2" />
          {user ? (
            <>
              <span className="text-sm text-muted max-w-[140px] truncate hidden lg:inline">
                {profile?.fullname ?? user.email}
              </span>
              <Button
                variant="outline"
                className="border-border text-foreground hover:bg-accent"
                onClick={() => void signOut()}
              >
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" className="border-border text-foreground hover:bg-accent" asChild>
                <Link to="/login">Log in</Link>
              </Button>
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90" asChild>
                <Link to="/signup">Sign up</Link>
              </Button>
            </>
          )}
        </nav>

        {/* Mobile Menu Button */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-card p-4 space-y-4">
          {showSearch && (
            <form onSubmit={handleSearch}>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                <Input
                  type="search"
                  placeholder="Search papers..."
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </form>
          )}
          <nav className="flex flex-col gap-2">
            <Button variant="ghost" asChild className="justify-start">
              <Link to="/search">Explore</Link>
            </Button>
            <Button variant="ghost" asChild className="justify-start">
              <Link to="/chat">Ask AI</Link>
            </Button>
            <Button variant="ghost" asChild className="justify-start">
              <Link to="/dashboard">Dashboard</Link>
            </Button>
            <div className="h-px bg-border my-2" />
            {user ? (
              <>
                <p className="text-sm text-muted px-2">{profile?.fullname ?? user.email}</p>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    void signOut();
                    setMobileMenuOpen(false);
                  }}
                >
                  Đăng xuất
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" className="w-full" asChild>
                  <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                    Đăng nhập
                  </Link>
                </Button>
                <Button className="w-full bg-primary text-primary-foreground" asChild>
                  <Link to="/signup" onClick={() => setMobileMenuOpen(false)}>
                    Đăng ký
                  </Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
