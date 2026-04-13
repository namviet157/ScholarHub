import { Library, Bookmark, Clock, MessageSquare, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import Header from "@/components/Header";
import PaperCard from "@/components/PaperCard";
import { useAuth } from "@/contexts/AuthContext";
import { useScholarPapers } from "@/hooks/useScholarPapers";
import { useDashboardStats } from "@/hooks/useDashboardStats";
import { useMemo, useState, useSyncExternalStore } from "react";
import { filterPapersByQuery } from "@/lib/papersRepository";
import type { Paper } from "@/types/scholar";
import {
  formatRelativeTime,
  getBookmarkIds,
  getQuestionLog,
  getReadingHistory,
  subscribeLibraryChanges,
} from "@/lib/userLibraryStorage";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";

function librarySnapshot(): string {
  const h = getReadingHistory();
  const q = getQuestionLog();
  return [getBookmarkIds().join(","), h.length, h[0]?.viewedAt ?? "", q.length, q[0]?.at ?? ""].join("|");
}

const Dashboard = () => {
  const navigate = useNavigate();
  const { profile, user } = useAuth();
  const { data: papers = [], isLoading, isError, error } = useScholarPapers();
  const stats = useDashboardStats();
  const [libraryQuery, setLibraryQuery] = useState("");
  const libRev = useSyncExternalStore(subscribeLibraryChanges, librarySnapshot, () => "");

  const displayName = profile?.fullname ?? user?.email ?? "Researcher";

  const libraryPapers = useMemo(
    () => filterPapersByQuery(papers, libraryQuery).slice(0, 80),
    [papers, libraryQuery]
  );

  const bookmarkedPapers = useMemo(() => {
    const ids = new Set(getBookmarkIds());
    if (ids.size === 0) return [];
    return papers.filter((p) => ids.has(p.id));
  }, [papers, libRev]);

  const historyEntries = useMemo(() => {
    const h = getReadingHistory();
    const byId = new Map(papers.map((p) => [p.id, p] as const));
    return h
      .map((e) => ({ entry: e, paper: byId.get(e.paperId) }))
      .filter((x): x is { entry: (typeof h)[number]; paper: Paper } => Boolean(x.paper))
      .slice(0, 30);
  }, [papers, libRev]);

  const questionLog = useMemo(() => getQuestionLog(), [libRev, stats.questions]);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Welcome back, {displayName}</h1>
          <p className="text-muted">Continue your research where you left off</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { icon: Library, label: "In catalog", value: isLoading ? "…" : String(papers.length) },
            { icon: Bookmark, label: "Bookmarks", value: String(stats.bookmarks) },
            { icon: Clock, label: "Read this week", value: String(stats.readThisWeek) },
            { icon: MessageSquare, label: "Questions", value: String(stats.questions) },
          ].map((stat) => (
            <Card key={stat.label} className="bg-card border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <stat.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{stat.value}</div>
                  <div className="text-sm text-muted">{stat.label}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Tabs defaultValue="library" className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <TabsList className="bg-card border border-border flex-wrap h-auto">
              <TabsTrigger
                value="library"
                className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                <Library className="h-4 w-4 mr-2" />
                My Library
              </TabsTrigger>
              <TabsTrigger
                value="bookmarks"
                className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                <Bookmark className="h-4 w-4 mr-2" />
                Bookmarks
              </TabsTrigger>
              <TabsTrigger
                value="history"
                className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                <Clock className="h-4 w-4 mr-2" />
                History
              </TabsTrigger>
              <TabsTrigger
                value="questions"
                className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Questions
              </TabsTrigger>
            </TabsList>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                <Input
                  placeholder="Search library..."
                  className="pl-9 bg-card border-border"
                  value={libraryQuery}
                  onChange={(e) => setLibraryQuery(e.target.value)}
                />
              </div>
              <Button
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                type="button"
                onClick={() => {
                  toast.message("Add papers", {
                    description: "Ingest PDFs with the Python pipeline, then refresh Explore.",
                  });
                  navigate("/search");
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Paper
              </Button>
            </div>
          </div>

          <TabsContent value="library" className="space-y-4">
            {isError && (
              <p className="text-sm text-destructive">
                {error instanceof Error ? error.message : "Could not load papers from Supabase."}
              </p>
            )}
            {isLoading && <p className="text-sm text-muted">Loading library…</p>}
            {!isLoading &&
              !isError &&
              libraryPapers.map((paper) => <PaperCard key={paper.id} paper={paper} />)}
            {!isLoading && !isError && libraryPapers.length === 0 && (
              <p className="text-sm text-muted">
                No papers match your search. Open Explore or check Supabase RLS policies.
              </p>
            )}
          </TabsContent>

          <TabsContent value="bookmarks" className="space-y-4">
            {bookmarkedPapers.length === 0 ? (
              <p className="text-sm text-muted">No bookmarks yet. Use the bookmark icon on a card or paper page.</p>
            ) : (
              bookmarkedPapers.map((paper) => <PaperCard key={paper.id} paper={paper} />)
            )}
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            {historyEntries.length === 0 ? (
              <p className="text-sm text-muted">Open a paper to build local reading history in this browser.</p>
            ) : (
              historyEntries.map(({ entry, paper }) => (
                <Card key={entry.paperId + entry.viewedAt} className="bg-card border-border">
                  <CardContent className="p-4 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <Link
                        to={`/paper/${paper.id}`}
                        className="font-medium text-foreground hover:text-primary line-clamp-2 block"
                      >
                        {paper.title}
                      </Link>
                      <p className="text-xs text-muted mt-1">{formatRelativeTime(entry.viewedAt)}</p>
                    </div>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/paper/${paper.id}`}>Open</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="questions">
            <Card className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-foreground">Recent questions</CardTitle>
                <Button variant="outline" size="sm" onClick={() => navigate("/search")}>
                  Explore papers
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {questionLog.length === 0 ? (
                  <p className="text-sm text-muted">
                    No questions yet. Open a paper and use the chat button (bottom-right).
                  </p>
                ) : (
                  questionLog.map((q) => (
                    <div
                      key={q.id}
                      className="p-4 rounded-lg bg-accent/50 border border-border hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-foreground mb-1">{q.question}</h4>
                          <p className="text-sm text-muted line-clamp-2 whitespace-pre-line">
                            {q.answer}
                          </p>
                        </div>
                        <span className="text-xs text-muted shrink-0">
                          {formatRelativeTime(q.at)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
