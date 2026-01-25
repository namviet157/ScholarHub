import { ArrowLeft, Bookmark, Share2, Download, Sparkles, MessageSquare, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import Header from "@/components/Header";
import { mockPapers } from "@/data/mockPapers";
import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";

const PaperViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState("Abstract");
  const [question, setQuestion] = useState("");

  const paper = mockPapers.find((p) => p.id === id) || mockPapers[0];

  const handleAskQuestion = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      navigate(`/chat?paper=${paper.id}&q=${encodeURIComponent(question)}`);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => navigate(-1)}
          className="mb-4 text-muted hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to results
        </Button>

        <div className="flex gap-8">
          {/* Left Sidebar - Table of Contents */}
          <aside className="hidden lg:block w-56 shrink-0">
            <div className="sticky top-24">
              <h3 className="font-semibold text-foreground mb-4">Contents</h3>
              <nav className="space-y-1">
                {paper.sections.map((section) => (
                  <button
                    key={section.title}
                    onClick={() => setActiveSection(section.title)}
                    className={`block w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      activeSection === section.title
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted hover:text-foreground hover:bg-accent"
                    }`}
                  >
                    {section.title}
                  </button>
                ))}
              </nav>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            <article className="bg-card border border-border rounded-xl p-8">
              {/* Paper Header */}
              <header className="mb-8 pb-8 border-b border-border">
                <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-4 leading-tight font-serif">
                  {paper.title}
                </h1>
                
                <p className="text-muted mb-4">
                  {paper.authors.join(", ")}
                </p>
                
                <div className="flex flex-wrap items-center gap-4 mb-6">
                  <Badge className="bg-primary/10 text-primary hover:bg-primary/20">
                    {paper.venue} {paper.year}
                  </Badge>
                  <span className="text-sm text-muted">
                    {paper.citations.toLocaleString()} citations
                  </span>
                </div>
                
                <div className="flex flex-wrap gap-2 mb-6">
                  {paper.keywords.map((keyword) => (
                    <Badge
                      key={keyword}
                      variant="outline"
                      className="border-border text-accent-foreground"
                    >
                      {keyword}
                    </Badge>
                  ))}
                </div>
                
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" className="border-border text-foreground hover:bg-accent">
                    <Bookmark className="h-4 w-4 mr-2" />
                    Save
                  </Button>
                  <Button variant="outline" size="sm" className="border-border text-foreground hover:bg-accent">
                    <Share2 className="h-4 w-4 mr-2" />
                    Share
                  </Button>
                  <Button variant="outline" size="sm" className="border-border text-foreground hover:bg-accent">
                    <Download className="h-4 w-4 mr-2" />
                    PDF
                  </Button>
                </div>
              </header>

              {/* Paper Content */}
              <div className="prose prose-slate max-w-none">
                {paper.sections.map((section) => (
                  <section key={section.title} className="mb-8">
                    <h2 className="text-xl font-semibold text-foreground mb-4 font-serif">
                      {section.title}
                    </h2>
                    <p className="text-accent-foreground leading-relaxed whitespace-pre-line">
                      {section.content}
                    </p>
                  </section>
                ))}
              </div>
            </article>
          </main>

          {/* Right Sidebar */}
          <aside className="hidden xl:block w-80 shrink-0 space-y-6">
            {/* AI Summary */}
            <Card className="bg-card border-border sticky top-24">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2 text-foreground">
                  <Sparkles className="h-4 w-4 text-primary" />
                  AI Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-accent-foreground leading-relaxed">
                  {paper.aiSummary}
                </p>
              </CardContent>
            </Card>

            {/* Keywords */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-base text-foreground">Keywords</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {paper.keywords.map((keyword) => (
                    <Badge
                      key={keyword}
                      className="bg-accent text-accent-foreground hover:bg-primary/10 hover:text-primary cursor-pointer"
                    >
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Ask Paper */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2 text-foreground">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  Ask This Paper
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAskQuestion}>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Ask a question..."
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      className="flex-1 bg-accent border-border text-foreground placeholder:text-muted"
                    />
                    <Button
                      type="submit"
                      size="icon"
                      className="bg-primary text-primary-foreground hover:bg-primary/90"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default PaperViewer;
