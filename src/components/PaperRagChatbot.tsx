import { Bot, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import { ragChatQuery, RAG_INSUFFICIENT_MESSAGE } from "@/lib/ragChatApi";
import { appendQuestionLog } from "@/lib/userLibraryStorage";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef, useState } from "react";

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
};

export type PaperRagChatbotProps = {
  arxivId?: string | null;
  /** Supabase `mongo_doc_id` — used as RAG fallback when vector chunks are empty. */
  mongoDocId?: string | null;
  paperTitle: string;
  paperId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  seedQuestion: string | null;
  onSeedConsumed?: () => void;
};

const MONGO_ID_RE = /^[a-f0-9]{24}$/i;

export function PaperRagChatbot({
  arxivId,
  mongoDocId,
  paperTitle,
  paperId,
  open,
  onOpenChange,
  seedQuestion,
  onSeedConsumed,
}: PaperRagChatbotProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [sending, setSending] = useState(false);
  const [composerTick, setComposerTick] = useState(0);
  const seedHandled = useRef<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    seedHandled.current = null;
  }, [paperId]);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(scrollToBottom, 50);
    return () => window.clearTimeout(t);
  }, [open, messages, sending, composerTick, scrollToBottom]);

  const runRag = useCallback(
    async (question: string): Promise<ChatMsg> => {
      const aid = (arxivId ?? "").trim();
      const mid = (mongoDocId ?? "").trim();
      const mongoIds = MONGO_ID_RE.test(mid) ? [mid] : [];

      if (!aid && mongoIds.length === 0) {
        return {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: RAG_INSUFFICIENT_MESSAGE,
        };
      }

      const res = await ragChatQuery({
        question,
        arxivIds: aid ? [aid] : [],
        paperTitles: [paperTitle],
        mongoDocIds: mongoIds,
      });

      if (!res.ok) {
        return {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: (res as { message: string }).message || RAG_INSUFFICIENT_MESSAGE,
        };
      }
      return {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
    },
    [arxivId, mongoDocId, paperTitle]
  );

  useEffect(() => {
    if (!open || !seedQuestion?.trim()) return;
    const q = seedQuestion.trim();
    if (seedHandled.current === q) return;
    seedHandled.current = q;

    const userMessage: ChatMsg = {
      id: `u-${Date.now()}`,
      role: "user",
      content: q,
    };
    setMessages((prev) => [...prev, userMessage]);
    setSending(true);
    void (async () => {
      try {
        const assistant = await runRag(q);
        appendQuestionLog({
          question: q,
          answer: assistant.content,
          paperIds: [paperId],
        });
        setMessages((prev) => [...prev, assistant]);
      } finally {
        setSending(false);
        onSeedConsumed?.();
      }
    })();
  }, [open, seedQuestion, runRag, paperId, onSeedConsumed]);

  const handleSendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || sending) return;

    const userMessage: ChatMsg = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setSending(true);
    try {
      const assistant = await runRag(trimmed);
      appendQuestionLog({
        question: trimmed,
        answer: assistant.content,
        paperIds: [paperId],
      });
      setMessages((prev) => [...prev, assistant]);
    } finally {
      setSending(false);
    }
  };

  const hasArxiv = Boolean((arxivId ?? "").trim());
  const hasMongo = Boolean((mongoDocId ?? "").trim() && MONGO_ID_RE.test((mongoDocId ?? "").trim()));

  const bumpComposer = useCallback(() => {
    setComposerTick((n) => n + 1);
  }, []);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3 pointer-events-none">
      {open && (
        <Card
          className={cn(
            "pointer-events-auto flex w-[min(calc(100vw-1.5rem),min(92vw,420px))] flex-col overflow-hidden",
            "h-[min(85dvh,640px)] max-h-[85dvh] border-border bg-card shadow-xl",
            "animate-scholarhub-chat-enter"
          )}
        >
          <div className="flex shrink-0 items-start justify-between gap-2 border-b border-border px-3 py-3">
            <div className="min-w-0">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Bot className="h-4 w-4 shrink-0 text-primary" />
                Ask this paper
              </h3>
              <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{paperTitle}</p>
              {hasArxiv ? (
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">arXiv:{arxivId}</p>
              ) : hasMongo ? (
                <p className="mt-1 text-[10px] text-muted-foreground">RAG via MongoDB document</p>
              ) : (
                <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">
                  No arXiv id or MongoDB link for RAG.
                </p>
              )}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0 text-muted-foreground hover:text-foreground"
              onClick={() => onOpenChange(false)}
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-4 p-3 pr-4">
              {messages.length === 0 && !sending ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Ask a question about this paper.
                </p>
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
              {sending && (
                <p className="animate-pulse text-center text-xs text-muted-foreground">
                  Retrieving context and generating…
                </p>
              )}
              <div ref={endRef} className="h-px w-full shrink-0" aria-hidden />
            </div>
          </ScrollArea>

          <div className="shrink-0 border-t border-border bg-card/95 p-3 backdrop-blur-sm">
            <ChatInput
              onSend={(m) => void handleSendMessage(m)}
              disabled={sending}
              placeholder="Ask about methods, results, notation…"
              showExploreLink={false}
              layout="panel"
              onComposerResize={bumpComposer}
            />
          </div>
        </Card>
      )}

      <Button
        type="button"
        size="icon"
        onClick={() => onOpenChange(!open)}
        className={cn(
          "pointer-events-auto h-14 w-14 rounded-full shadow-lg transition-transform duration-200 hover:scale-105",
          "bg-primary text-primary-foreground hover:bg-primary/90"
        )}
        aria-expanded={open}
        aria-label={open ? "Close paper chat" : "Open paper chat"}
      >
        {open ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </Button>
    </div>
  );
}
