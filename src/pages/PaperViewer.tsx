import { ArrowLeft, Share2, Download, Sparkles, Info, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import Header from "@/components/Header";
import { LatexContent } from "@/components/LatexContent";
import { PaperRagChatbot } from "@/components/PaperRagChatbot";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useScholarPaperDetail } from "@/hooks/useScholarPaperDetail";
import { recordPaperView } from "@/lib/userLibraryStorage";
import type { Paper } from "@/types/scholar";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function abstractTeaser(abstract: string, max = 420): string {
  const t = abstract.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max).trimEnd()}…`;
}

function PaperMetadataSidebar({ paper }: { paper: Paper }) {
  const abs = paper.abstract?.trim() ?? "";

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Abstract
        </h3>
        <p className="text-sm leading-relaxed text-slate-900 dark:text-slate-50">
          {abs ? abstractTeaser(abs) : "—"}
        </p>
      </div>

      <Card className="border-sky-200/80 bg-sky-50/90 shadow-sm dark:border-sky-900/50 dark:bg-sky-950/35">
        <CardHeader className="pb-2 pt-4">
          <CardTitle className="flex items-center gap-2 text-base text-slate-900 dark:text-slate-50">
            <Sparkles className="h-4 w-4 text-sky-600 dark:text-sky-400" />
            AI Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 text-sm text-slate-800 dark:text-slate-100">
          {paper.aiSummary ? (
            <LatexContent text={paper.aiSummary} />
          ) : (
            <span className="text-slate-500 dark:text-slate-400">—</span>
          )}
        </CardContent>
      </Card>

      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Keywords
        </h3>
        {paper.keywords.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">—</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {paper.keywords.map((keyword) => (
              <Badge
                key={keyword}
                className="border-0 bg-slate-200/90 px-2.5 py-0.5 text-xs font-medium text-slate-900 shadow-sm hover:bg-slate-300/90 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
              >
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200/90 bg-white/60 p-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
        <p className="font-mono">{paper.arxivId ?? "—"}</p>
        <p className="mt-1">
          {paper.venue} · {paper.year}
        </p>
      </div>
    </div>
  );
}

const PaperViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useScholarPaperDetail(id);
  const paper = data?.paper;
  const mongoAvailable = data?.mongoAvailable ?? false;
  const [sectionIndex, setSectionIndex] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatSeed, setChatSeed] = useState<string | null>(null);
  const urlSeedDone = useRef(false);
  const clearChatSeed = useCallback(() => setChatSeed(null), []);

  useEffect(() => {
    setSectionIndex(0);
    urlSeedDone.current = false;
  }, [id]);

  useEffect(() => {
    if (paper) {
      recordPaperView(paper.id, paper.title);
    }
  }, [paper?.id, paper?.title]);

  useEffect(() => {
    if (!paper?.id || urlSeedDone.current) return;
    const q = new URLSearchParams(window.location.search).get("q")?.trim();
    if (!q) return;
    urlSeedDone.current = true;
    setChatSeed(q);
    setChatOpen(true);
    navigate(`/paper/${paper.id}`, { replace: true });
  }, [paper?.id, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-4 py-12 text-muted-foreground">Loading paper…</div>
      </div>
    );
  }

  if (isError || !paper) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto space-y-4 px-4 py-12">
          <p className="text-destructive">
            {isError && error instanceof Error ? error.message : "Paper not found."}
          </p>
          <Button variant="outline" asChild>
            <Link to="/">Back to Explore</Link>
          </Button>
        </div>
      </div>
    );
  }

  const scrollToSection = (i: number) => {
    setSectionIndex(i);
    document.getElementById(`paper-section-${paper.id}-${i}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  const handleShare = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title: paper.title, text: paper.title, url });
        return;
      }
    } catch {
      /* dismissed or unsupported */
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied to clipboard.");
    } catch {
      toast.error("Could not share or copy the link.");
    }
  };

  const sidebarInner = <PaperMetadataSidebar paper={paper} />;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-5 pb-28 lg:flex lg:min-h-0 lg:flex-col lg:py-6 lg:h-[calc(100dvh-4rem)] lg:max-h-[calc(100dvh-4rem)] lg:overflow-hidden">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => navigate(-1)}
            className="text-muted-foreground hover:text-foreground -ml-2"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="gap-1.5 lg:hidden border-border">
                <Info className="h-4 w-4" />
                Paper details
              </Button>
            </SheetTrigger>
            <SheetContent
              side="bottom"
              className="max-h-[90dvh] overflow-y-auto rounded-t-2xl border-t border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50"
            >
              <SheetHeader className="text-left">
                <SheetTitle className="text-slate-900 dark:text-slate-50">Paper details</SheetTitle>
              </SheetHeader>
              <div className="mt-6 px-1 pb-8">{sidebarInner}</div>
            </SheetContent>
          </Sheet>
        </div>

        {!mongoAvailable && (
          <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-foreground">
            Full-text excerpts from MongoDB are not available for this record.
          </div>
        )}

        <div className="flex min-h-0 flex-1 flex-col gap-6 lg:flex-row lg:gap-6">
          {/* Left 70% — only this column scrolls on desktop */}
          <div className="order-1 flex min-h-0 w-full min-w-0 flex-col lg:order-1 lg:w-[70%] lg:flex-none lg:overflow-y-auto lg:overscroll-contain lg:pr-3">
            <article className="rounded-xl border border-border bg-card p-5 sm:p-8">
              <header className="mb-6 border-b border-border pb-6">
                <h1 className="mb-4 font-serif text-2xl font-bold leading-tight text-slate-900 dark:text-slate-50 sm:text-3xl">
                  {paper.title}
                </h1>
                <p className="mb-4 text-slate-600 dark:text-slate-300">
                  {paper.authors.length > 0 ? paper.authors.join(", ") : "—"}
                </p>
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <Badge className="bg-primary/15 text-primary hover:bg-primary/20">
                    {paper.venue} {paper.year}
                  </Badge>
                  {paper.arxivId && (
                    <span className="font-mono text-sm text-muted-foreground">{paper.arxivId}</span>
                  )}
                  {paper.citations > 0 && (
                    <span className="text-sm text-muted-foreground">
                      {paper.citations.toLocaleString()} citations
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    className="border-border"
                    onClick={() => void handleShare()}
                  >
                    <Share2 className="mr-2 h-4 w-4" />
                    Share
                  </Button>
                  {paper.pdfUrl ? (
                    <Button variant="outline" size="sm" className="border-border" asChild>
                      <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer">
                        <Download className="mr-2 h-4 w-4" />
                        PDF
                      </a>
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" className="text-muted-foreground" disabled>
                      <Download className="mr-2 h-4 w-4" />
                      PDF
                    </Button>
                  )}
                </div>
              </header>

              <div className="sticky top-0 z-10 -mx-2 mb-6 border-b border-border bg-card/95 px-2 py-3 backdrop-blur supports-[backdrop-filter]:bg-card/80 lg:static lg:mb-8 lg:border-0 lg:bg-transparent lg:px-0 lg:py-0 lg:backdrop-blur-none">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <List className="h-3.5 w-3.5" />
                  Contents
                </div>
                <nav className="flex flex-wrap gap-2 lg:flex-col lg:flex-nowrap lg:gap-1">
                  {paper.sections.map((section, i) => (
                    <button
                      key={`${section.title}-${i}`}
                      type="button"
                      onClick={() => scrollToSection(i)}
                      className={cn(
                        "rounded-lg px-3 py-2 text-left text-sm transition-colors",
                        sectionIndex === i
                          ? "bg-primary/15 font-medium text-primary"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      )}
                    >
                      {section.title}
                    </button>
                  ))}
                </nav>
              </div>

              <div className="prose prose-slate max-w-none dark:prose-invert">
                {paper.sections.map((section, i) => (
                  <section
                    key={`${section.title}-${i}`}
                    id={`paper-section-${paper.id}-${i}`}
                    className="mb-8 scroll-mt-28"
                  >
                    <h2 className="mb-4 font-serif text-xl font-semibold text-slate-900 dark:text-slate-50">
                      {section.title}
                    </h2>
                    <div className="text-slate-800 dark:text-slate-200">
                      <LatexContent text={section.content} />
                    </div>
                  </section>
                ))}
              </div>
            </article>
          </div>

          {/* Right 30% — sticky metadata; desktop only inline */}
          <aside className="order-2 hidden w-full shrink-0 lg:order-2 lg:block lg:w-[30%] lg:flex-none">
            <div
              className="sticky top-20 z-10 max-h-[calc(100dvh-5.5rem)] overflow-y-auto overscroll-contain rounded-2xl border border-slate-200/90 bg-slate-50 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950 lg:top-24"
              style={{ scrollbarGutter: "stable" }}
            >
              {sidebarInner}
            </div>
          </aside>
        </div>
      </div>

      <PaperRagChatbot
        arxivId={paper.arxivId}
        mongoDocId={paper.mongoDocId}
        paperTitle={paper.title}
        paperId={paper.id}
        open={chatOpen}
        onOpenChange={setChatOpen}
        seedQuestion={chatSeed}
        onSeedConsumed={clearChatSeed}
      />
    </div>
  );
};

export default PaperViewer;
