import { Send, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useState, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
  /** When false, hides the “Pick paper” control (e.g. embedded on a single paper page). */
  showExploreLink?: boolean;
}

const ChatInput = ({
  onSend,
  placeholder = "Ask a question about your papers...",
  disabled,
  showExploreLink = true,
}: ChatInputProps) => {
  const [message, setMessage] = useState("");

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

  return (
    <div className="border border-border rounded-xl bg-card p-3 shadow-sm">
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="min-h-[60px] max-h-[200px] resize-none border-0 bg-transparent p-0 focus-visible:ring-0 text-foreground placeholder:text-muted"
        disabled={disabled}
      />
      <div
        className={cn(
          "flex items-center mt-3 pt-3 border-t border-border",
          showExploreLink ? "justify-between" : "justify-end"
        )}
      >
        {showExploreLink && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-muted hover:text-primary"
            onClick={() => navigate("/search")}
          >
            <Paperclip className="h-4 w-4 mr-2" />
            Pick paper
          </Button>
        )}
        <Button
          onClick={handleSend}
          disabled={!message.trim() || disabled}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Send className="h-4 w-4 mr-2" />
          Send
        </Button>
      </div>
    </div>
  );
};

export default ChatInput;
