import { ArrowLeft, Bookmark, Share2, Download, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

import { Badge } from "@/components/ui/badge";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import Header from "@/components/Header";

import { LatexContent } from "@/components/LatexContent";

import { PaperRagChatbot } from "@/components/PaperRagChatbot";

import { useParams, useNavigate, Link } from "react-router-dom";

import { useCallback, useEffect, useRef, useState } from "react";

import { useScholarPaperDetail } from "@/hooks/useScholarPaperDetail";

import { useBookmark } from "@/hooks/useBookmark";

import { recordPaperView } from "@/lib/userLibraryStorage";

import { toast } from "sonner";

import { cn } from "@/lib/utils";



const PaperViewer = () => {

  const { id } = useParams();

  const navigate = useNavigate();

  const { data, isLoading, isError, error } = useScholarPaperDetail(id);

  const paper = data?.paper;

  const mongoAvailable = data?.mongoAvailable ?? false;

  const { bookmarked, toggle } = useBookmark(id);

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

        <div className="container mx-auto px-4 py-12 text-muted">Loading paper…</div>

      </div>

    );

  }



  if (isError || !paper) {

    return (

      <div className="min-h-screen bg-background">

        <Header />

        <div className="container mx-auto px-4 py-12 space-y-4">

          <p className="text-destructive">

            {isError && error instanceof Error ? error.message : "Paper not found."}

          </p>

          <Button variant="outline" asChild>

            <Link to="/search">Back to Explore</Link>

          </Button>

        </div>

      </div>

    );

  }



  const scrollToSection = (i: number) => {

    setSectionIndex(i);

    document

      .getElementById(`paper-section-${paper.id}-${i}`)

      ?.scrollIntoView({ behavior: "smooth", block: "start" });

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



  const toggleSave = () => {

    const was = bookmarked;

    toggle();

    toast.success(was ? "Removed from saved." : "Saved to bookmarks.");

  };



  return (

    <div className="min-h-screen bg-background">

      <Header />



      <div className="container mx-auto px-4 py-6 pb-24">

        <Button

          variant="ghost"

          onClick={() => navigate(-1)}

          className="mb-4 text-muted hover:text-foreground"

        >

          <ArrowLeft className="h-4 w-4 mr-2" />

          Back to results

        </Button>



        <div className="mb-4 space-y-2">

          <div className="rounded-lg border border-border bg-accent/30 px-4 py-3 text-sm text-foreground">

            <strong className="font-medium">Ask this paper:</strong> use the chat button (bottom-right). Each

            message is sent with this paper&apos;s <span className="font-mono text-xs">arxiv_id</span> to the RAG

            API (pgvector chunks).

          </div>

          {!mongoAvailable && (

            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-foreground">

              Full-text excerpts from MongoDB are not available for this record. The viewer may show metadata only;

              vector RAG still works if chunks were embedded for this arXiv id.

            </div>

          )}

        </div>



        <div className="flex gap-8">

          <aside className="hidden lg:block w-56 shrink-0">

            <div className="sticky top-24">

              <h3 className="font-semibold text-foreground mb-4">Contents</h3>

              <nav className="space-y-1">

                {paper.sections.map((section, i) => (

                  <button

                    key={`${section.title}-${i}`}

                    type="button"

                    onClick={() => scrollToSection(i)}

                    className={cn(

                      "block w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",

                      sectionIndex === i

                        ? "bg-primary/10 text-primary font-medium"

                        : "text-muted hover:text-foreground hover:bg-accent"

                    )}

                  >

                    {section.title}

                  </button>

                ))}

              </nav>

            </div>

          </aside>



          <main className="flex-1 min-w-0">

            <article className="bg-card border border-border rounded-xl p-8">

              <header className="mb-8 pb-8 border-b border-border">

                <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-4 leading-tight font-serif">

                  {paper.title}

                </h1>



                <p className="text-muted mb-4">

                  {paper.authors.length > 0 ? paper.authors.join(", ") : "—"}

                </p>



                <div className="flex flex-wrap items-center gap-4 mb-6">

                  <Badge className="bg-primary/10 text-primary hover:bg-primary/20">

                    {paper.venue} {paper.year}

                  </Badge>

                  {paper.arxivId && (

                    <span className="text-sm text-muted font-mono">{paper.arxivId}</span>

                  )}

                  {paper.citations > 0 && (

                    <span className="text-sm text-muted">

                      {paper.citations.toLocaleString()} citations

                    </span>

                  )}

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

                  <Button

                    variant="outline"

                    size="sm"

                    type="button"

                    className={cn("border-border", bookmarked && "border-primary text-primary")}

                    onClick={toggleSave}

                  >

                    <Bookmark className={cn("h-4 w-4 mr-2", bookmarked && "fill-primary")} />

                    {bookmarked ? "Saved" : "Save"}

                  </Button>

                  <Button

                    variant="outline"

                    size="sm"

                    type="button"

                    className="border-border text-foreground hover:bg-accent"

                    onClick={() => void handleShare()}

                  >

                    <Share2 className="h-4 w-4 mr-2" />

                    Share

                  </Button>

                  {paper.pdfUrl ? (

                    <Button

                      variant="outline"

                      size="sm"

                      className="border-border text-foreground hover:bg-accent"

                      asChild

                    >

                      <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer">

                        <Download className="h-4 w-4 mr-2" />

                        PDF

                      </a>

                    </Button>

                  ) : (

                    <Button variant="outline" size="sm" className="border-border text-muted" disabled>

                      <Download className="h-4 w-4 mr-2" />

                      PDF

                    </Button>

                  )}

                </div>

              </header>



              <div className="prose prose-slate max-w-none">

                {paper.sections.map((section, i) => (

                  <section

                    key={`${section.title}-${i}`}

                    id={`paper-section-${paper.id}-${i}`}

                    className="mb-8 scroll-mt-28"

                  >

                    <h2 className="text-xl font-semibold text-foreground mb-4 font-serif">

                      {section.title}

                    </h2>

                    <div className="text-accent-foreground">

                      <LatexContent text={section.content} />

                    </div>

                  </section>

                ))}

              </div>

            </article>

          </main>



          <aside className="hidden xl:block w-80 shrink-0">

            <div className="sticky top-24 space-y-6 z-10">

              <Card className="bg-card border-border">

                <CardHeader className="pb-3">

                  <CardTitle className="text-base flex items-center gap-2 text-foreground">

                    <Sparkles className="h-4 w-4 text-primary" />

                    AI Summary

                  </CardTitle>

                </CardHeader>

                <CardContent>

                  {paper.aiSummary ? (

                    <LatexContent text={paper.aiSummary} className="text-sm text-accent-foreground" />

                  ) : (

                    <p className="text-sm text-muted">—</p>

                  )}

                </CardContent>

              </Card>

              <Card className="bg-card border-border">

                <CardHeader className="pb-3">

                  <CardTitle className="text-base text-foreground">Keywords</CardTitle>

                </CardHeader>

                <CardContent>

                  <div className="flex flex-wrap gap-2">

                    {paper.keywords.length === 0 ? (

                      <span className="text-sm text-muted">—</span>

                    ) : (

                      paper.keywords.map((keyword) => (

                        <Badge

                          key={keyword}

                          className="bg-accent text-accent-foreground hover:bg-primary/10 hover:text-primary cursor-pointer"

                        >

                          {keyword}

                        </Badge>

                      ))

                    )}

                  </div>

                </CardContent>

              </Card>

            </div>

          </aside>

        </div>

      </div>



      <PaperRagChatbot

        arxivId={paper.arxivId}

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

