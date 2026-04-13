import { Send, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useState, KeyboardEvent, useRef, useLayoutEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
  showExploreLink?: boolean;
  layout?: "default" | "panel";
  /** Called after textarea height is recalculated (for scroll-to-bottom in parent). */
  onComposerResize?: () => void;
}

const ChatInput = ({
  onSend,
  placeholder = "Ask a question about your papers...",
  disabled,
  showExploreLink = true,
  layout = "default",
  onComposerResize,
}: ChatInputProps) => {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  const minH = layout === "panel" ? 48 : 60;
  const maxH = layout === "panel" ? 176 : 200;

  const syncHeight = useCallback(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "0px";
    const next = Math.max(minH, Math.min(el.scrollHeight, maxH));
    el.style.height = `${next}px`;
    onComposerResize?.();
  }, [minH, maxH, onComposerResize]);

  useLayoutEffect(() => {
    syncHeight();
  }, [message, layout, disabled, syncHeight]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isPanel = layout === "panel";

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card shadow-sm",
        isPanel ? "p-2 sm:p-3" : "p-3"
      )}
    >
      <Textarea
        ref={taRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        className={cn(
          "min-h-0 resize-none overflow-y-auto border-0 bg-transparent px-1 py-2 text-sm leading-relaxed",
          "text-foreground placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0",
          "max-h-[11rem]"
        )}
        style={{ height: minH }}
        disabled={disabled}
      />
      <div
        className={cn(
          "flex items-center gap-2 border-t border-border/80 pt-2 mt-1",
          showExploreLink ? "justify-between" : "justify-end"
        )}
      >
        {showExploreLink && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-primary h-8"
            onClick={() => navigate("/")}
          >
            <Paperclip className="h-4 w-4 mr-2" />
            Pick paper
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          onClick={handleSend}
          disabled={!message.trim() || disabled}
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-8"
        >
          <Send className="h-4 w-4 mr-2" />
          Send
        </Button>
      </div>
    </div>
  );
};

export default ChatInput;
