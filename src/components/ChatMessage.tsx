import { User, Bot, Quote, Copy, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { LatexContent } from "@/components/LatexContent";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

const ChatMessage = ({ role, content, citations }: ChatMessageProps) => {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Copied to clipboard");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy");
    }
  };

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-slate-200 text-slate-900 dark:bg-slate-700 dark:text-slate-50" : "bg-primary/15 text-primary"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={cn("min-w-0 flex-1", isUser ? "flex flex-col items-end" : "flex flex-col items-start")}>
        <div
          className={cn(
            "relative max-w-[min(100%,28rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
            isUser
              ? "rounded-tr-md bg-primary text-primary-foreground"
              : "rounded-tl-md border border-slate-200/90 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50"
          )}
        >
          {!isUser && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1 h-7 w-7 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              aria-label="Copy message"
              onClick={() => void handleCopy()}
            >
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            </Button>
          )}
          <div className={cn(!isUser && "pr-8")}>
            {isUser ? (
              <div className="whitespace-pre-wrap">{content}</div>
            ) : (
              <LatexContent text={content} />
            )}
          </div>
        </div>

        {!isUser && citations && citations.length > 0 && (
          <details className="mt-2 max-w-[min(100%,28rem)] rounded-lg border border-slate-200/80 bg-slate-50/90 text-slate-800 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 [&::-webkit-details-marker]:hidden">
              <Quote className="h-3.5 w-3.5 shrink-0 text-primary" />
              <span>Citations ({citations.length})</span>
            </summary>
            <ul className="space-y-1.5 border-t border-slate-200/80 px-3 py-2 dark:border-slate-700">
              {citations.map((citation, index) => (
                <li key={index} className="text-xs leading-snug text-slate-700 dark:text-slate-300 pl-2 border-l-2 border-primary/40">
                  {citation}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
