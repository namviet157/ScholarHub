import { User, Bot, Quote } from "lucide-react";
import { cn } from "@/lib/utils";
import { LatexContent } from "@/components/LatexContent";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

const ChatMessage = ({ role, content, citations }: ChatMessageProps) => {
  const isUser = role === "user";

  return (
    <div className={cn("flex gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "w-10 h-10 rounded-full flex items-center justify-center shrink-0",
          isUser ? "bg-secondary" : "bg-primary/10"
        )}
      >
        {isUser ? (
          <User className="h-5 w-5 text-secondary-foreground" />
        ) : (
          <Bot className="h-5 w-5 text-primary" />
        )}
      </div>

      <div
        className={cn(
          "flex-1 max-w-[80%]",
          isUser ? "text-right" : "text-left"
        )}
      >
        <div
          className={cn(
            "inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-full text-left",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-card border border-border text-foreground rounded-tl-sm"
          )}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{content}</div>
          ) : (
            <LatexContent text={content} />
          )}
        </div>

        {citations && citations.length > 0 && (
          <div className="mt-2 space-y-1">
            {citations.map((citation, index) => (
              <div
                key={index}
                className="flex items-center gap-2 text-xs text-muted hover:text-primary transition-colors cursor-pointer"
              >
                <Quote className="h-3 w-3" />
                <span>{citation}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
