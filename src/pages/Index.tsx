import { Search, Sparkles, MessageSquare, Quote, ArrowRight, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Header from "@/components/Header";
import FeatureCard from "@/components/FeatureCard";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePaperCount } from "@/hooks/usePaperCount";
import { toast } from "sonner";

const Index = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const { data: catalogCount, isLoading: countLoading } = usePaperCount();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  const features = [
    {
      icon: Search,
      title: "Semantic Paper Search",
      description: "Find relevant research papers using natural language queries. Our AI understands context and meaning.",
    },
    {
      icon: Sparkles,
      title: "AI Summaries",
      description: "Get instant, comprehensive summaries of complex papers. Save hours of reading time.",
    },
    {
      icon: MessageSquare,
      title: "Ask Your Papers",
      description: "Chat with your documents. Ask questions and get answers with citations from your library.",
    },
    {
      icon: Quote,
      title: "Smart References",
      description: "Automatically extract and organize citations. Build your bibliography effortlessly.",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header showSearch={false} />

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
        <div className="container mx-auto px-4 pt-20 pb-24">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-2 text-sm font-medium mb-6">
              <Sparkles className="h-4 w-4" />
              AI-Powered Research Platform
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground mb-6 leading-tight">
              ScholarHub – Your{" "}
              <span className="text-primary">AI Research</span>{" "}
              Companion
            </h1>
            
            <p className="text-lg sm:text-xl text-muted max-w-2xl mx-auto mb-10 leading-relaxed">
              Search, read, and understand scientific papers with AI-powered tools. 
              Accelerate your research with intelligent summaries and document chat.
            </p>

            {/* Main Search Box */}
            <form onSubmit={handleSearch} className="max-w-2xl mx-auto mb-8">
              <div className="relative group">
                <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative bg-card border border-border rounded-2xl p-2 shadow-lg">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 relative">
                      <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted" />
                      <Input
                        type="search"
                        placeholder="Search papers, topics, authors..."
                        className="pl-12 h-14 text-lg border-0 bg-transparent focus-visible:ring-0 text-foreground placeholder:text-muted"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                    </div>
                    <Button
                      type="submit"
                      size="lg"
                      className="h-12 px-6 bg-primary text-primary-foreground hover:bg-primary/90"
                    >
                      Search
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </form>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="bg-primary text-primary-foreground hover:bg-primary/90 px-8"
                onClick={() => navigate("/search")}
              >
                Start Exploring
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                type="button"
                className="border-border text-foreground hover:bg-accent px-8"
                onClick={() => {
                  toast.message("Ingestion", {
                    description:
                      "Use the Python pipeline (batch / Supabase / Mongo) to add papers. Then refresh Explore.",
                  });
                  navigate("/search");
                }}
              >
                <Upload className="mr-2 h-4 w-4" />
                Upload a Paper
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-accent/50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Powerful AI Tools for Researchers
            </h2>
            <p className="text-muted max-w-2xl mx-auto">
              Everything you need to accelerate your research workflow
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {features.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto text-center">
            {[
              {
                value: countLoading ? "…" : catalogCount != null ? String(catalogCount) : "—",
                label: "Papers in your catalog",
              },
              { value: "AI", label: "Summaries & chat" },
              { value: "Local", label: "Bookmarks & history" },
              { value: "Open", label: "Supabase + Mongo" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl sm:text-4xl font-bold text-primary mb-2">
                  {stat.value}
                </div>
                <div className="text-muted text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 bg-card">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-lg">S</span>
              </div>
              <span className="font-semibold text-lg text-foreground">ScholarHub</span>
            </div>
            <p className="text-muted text-sm">© {new Date().getFullYear()} ScholarHub</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
