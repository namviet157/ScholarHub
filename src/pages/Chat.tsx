import { Bot, FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import Header from "@/components/Header";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import { useScholarPapers } from "@/hooks/useScholarPapers";
import { buildAnswerFromPapers } from "@/lib/chatHeuristics";
import { appendQuestionLog } from "@/lib/userLibraryStorage";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: string[];
};

const Chat = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const focusPaperId = searchParams.get("paper");
  const seedQ = searchParams.get("q");

  const { data: papers = [], isLoading } = useScholarPapers();
  const [excluded, setExcluded] = useState<Set<string>>(() => new Set());
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const seededRef = useRef(false);

  const selectedPapers = useMemo(() => {
    const pool = papers.filter((p) => !excluded.has(p.id));
    const ordered = [...pool];
    if (focusPaperId) {
      const ix = ordered.findIndex((p) => p.id === focusPaperId);
      if (ix > 0) {
        const [picked] = ordered.splice(ix, 1);
        ordered.unshift(picked);
      }
    }
    return ordered.slice(0, 2);
  }, [papers, excluded, focusPaperId]);

  useEffect(() => {
    if (seededRef.current || !seedQ?.trim() || isLoading) return;
    if (selectedPapers.length === 0) return;
    seededRef.current = true;
    const q = seedQ.trim();
    const { answer, citations } = buildAnswerFromPapers(q, selectedPapers);
    appendQuestionLog({ question: q, answer, paperIds: selectedPapers.map((p) => p.id) });
    setMessages([
      { id: `u-${Date.now()}`, role: "user", content: q, timestamp: new Date() },
      {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: answer,
        timestamp: new Date(),
        citations,
      },
    ]);
  }, [seedQ, selectedPapers, isLoading]);

  const handleSendMessage = (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const { answer, citations } = buildAnswerFromPapers(trimmed, selectedPapers);
    appendQuestionLog({ question: trimmed, answer, paperIds: selectedPapers.map((p) => p.id) });

    const userMessage: ChatMsg = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    const aiResponse: ChatMsg = {
      id: `a-${Date.now() + 1}`,
      role: "assistant",
      content: answer,
      timestamp: new Date(),
      citations,
    };
    setMessages((prev) => [...prev, userMessage, aiResponse]);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <div className="flex-1 container mx-auto px-4 py-6 flex gap-6 max-h-[calc(100vh-5rem)]">
        <aside className="hidden lg:block w-72 shrink-0">
          <Card className="h-full bg-card border-border">
            <div className="p-4 border-b border-border">
              <h2 className="font-semibold text-foreground flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                Context papers ({selectedPapers.length})
              </h2>
              <p className="text-xs text-muted mt-1">
                Answers use abstracts from up to two papers. Remove one to rotate the queue.
              </p>
            </div>
            <ScrollArea className="h-[calc(100%-5rem)] p-4">
              <div className="space-y-3">
                {isLoading && <p className="text-sm text-muted">Loading catalog…</p>}
                {!isLoading && selectedPapers.length === 0 && (
                  <p className="text-sm text-muted">No papers in context. Add papers from Explore.</p>
                )}
                {selectedPapers.map((paper) => (
                  <div
                    key={paper.id}
                    className="p-3 rounded-lg bg-accent/50 border border-border hover:border-primary/30 transition-colors group"
                  >
                    <h3 className="text-sm font-medium text-foreground line-clamp-2 mb-1">{paper.title}</h3>
                    <p className="text-xs text-muted">
                      {paper.authors[0] ?? "—"}
                      {paper.authors.length > 1 ? " et al." : ""}, {paper.year}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      type="button"
                      className="w-full mt-2 text-muted hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => setExcluded((prev) => new Set(prev).add(paper.id))}
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      Remove from context
                    </Button>
                  </div>
                ))}

                <Button
                  variant="outline"
                  type="button"
                  className="w-full border-dashed border-border text-muted hover:text-foreground"
                  onClick={() => navigate("/search")}
                >
                  + Add papers
                </Button>
              </div>
            </ScrollArea>
          </Card>
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          <Card className="flex-1 flex flex-col bg-card border-border overflow-hidden">
            <div className="p-4 border-b border-border flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="font-semibold text-foreground">ScholarHub Q&A</h2>
                <p className="text-sm text-muted">Heuristic answers from your catalog (plug in an LLM later).</p>
              </div>
            </div>

            <ScrollArea className="flex-1 p-6">
              <div className="space-y-6 max-w-3xl mx-auto">
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <Bot className="h-12 w-12 text-muted mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-foreground mb-2">Ask your papers</h3>
                    <p className="text-muted max-w-md mx-auto text-sm">
                      Questions are matched to the papers on the left; responses pull from titles and abstracts.
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      role={message.role}
                      content={message.content}
                      citations={message.role === "assistant" ? message.citations : undefined}
                    />
                  ))
                )}
              </div>
            </ScrollArea>

            <div className="p-4 border-t border-border">
              <div className="max-w-3xl mx-auto">
                <ChatInput onSend={handleSendMessage} disabled={isLoading && papers.length === 0} />
              </div>
            </div>
          </Card>
        </main>
      </div>
    </div>
  );
};

export default Chat;
