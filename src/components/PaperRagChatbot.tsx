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
  paperTitle: string;
  paperId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** When set (e.g. from inline ask), panel should open and send this question once */
  seedQuestion: string | null;
  onSeedConsumed?: () => void;
};

export function PaperRagChatbot({
  arxivId,
  paperTitle,
  paperId,
  open,
  onOpenChange,
  seedQuestion,
  onSeedConsumed,
}: PaperRagChatbotProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [sending, setSending] = useState(false);
  const seedHandled = useRef<string | null>(null);

  useEffect(() => {
    setMessages([]);
    seedHandled.current = null;
  }, [paperId]);

  const runRag = useCallback(
    async (question: string): Promise<ChatMsg> => {
      const aid = (arxivId ?? "").trim();
      if (!aid) {
        return {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: RAG_INSUFFICIENT_MESSAGE,
        };
      }
      const res = await ragChatQuery({
        question,
        arxivIds: [aid],
        paperTitles: [paperTitle],
      });
      if (!res.ok) {
        return {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: res.message,
        };
      }
      return {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
    },
    [arxivId, paperTitle]
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

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3 pointer-events-none">
      <Card
        className={cn(
          "pointer-events-auto flex flex-col overflow-hidden border-border bg-card shadow-xl transition-all duration-200",
          "w-[min(calc(100vw-2rem),420px)] h-[min(70vh,520px)]",
          !open && "hidden"
        )}
      >
        <div className="flex items-start justify-between gap-2 border-b border-border p-3 shrink-0">
          <div className="min-w-0">
            <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
              <Bot className="h-4 w-4 text-primary shrink-0" />
              Ask this paper
            </h3>
            <p className="text-xs text-muted line-clamp-2 mt-0.5">{paperTitle}</p>
            {hasArxiv ? (
              <p className="text-[10px] font-mono text-muted mt-1">arXiv:{arxivId}</p>
            ) : (
              <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
                No arXiv id — RAG needs an arXiv id and indexed chunks.
              </p>
            )}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0 text-muted hover:text-foreground"
            onClick={() => onOpenChange(false)}
            aria-label="Close chat"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1 min-h-0 p-3">
          <div className="space-y-4 pr-2">
            {messages.length === 0 && !sending ? (
              <p className="text-sm text-muted text-center py-6">
                Ask a question about this paper. Answers use RAG over vector chunks for this arXiv id.
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
              <p className="text-xs text-muted text-center animate-pulse">Retrieving context and generating…</p>
            )}
          </div>
        </ScrollArea>

        <div className="p-3 border-t border-border shrink-0">
          <ChatInput
            onSend={(m) => void handleSendMessage(m)}
            disabled={sending}
            placeholder="Ask about methods, results, notation…"
            showExploreLink={false}
          />
        </div>
      </Card>

      <Button
        type="button"
        size="icon"
        onClick={() => onOpenChange(!open)}
        className={cn(
          "pointer-events-auto h-14 w-14 rounded-full shadow-lg",
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
