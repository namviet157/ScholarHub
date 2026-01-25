import { Bot, FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import Header from "@/components/Header";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import { mockChatHistory, mockPapers } from "@/data/mockPapers";
import { useState } from "react";

const Chat = () => {
  const [messages, setMessages] = useState(mockChatHistory);
  const [selectedPapers, setSelectedPapers] = useState(mockPapers.slice(0, 2));

  const handleSendMessage = (content: string) => {
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content,
      timestamp: new Date(),
    };

    const aiResponse = {
      id: (Date.now() + 1).toString(),
      role: "assistant" as const,
      content: `Based on my analysis of the selected papers, I can provide the following insights:\n\n${content.toLowerCase().includes("transformer") ? "The Transformer architecture introduced in 'Attention Is All You Need' fundamentally changed NLP by enabling parallel processing of sequences through self-attention mechanisms. This has led to significant improvements in translation quality and training efficiency." : "This is a complex question that touches on multiple aspects of the research. The papers in your library provide complementary perspectives on this topic. Would you like me to elaborate on any specific aspect?"}`,
      timestamp: new Date(),
      citations: ["Vaswani et al., 2017", "Devlin et al., 2019"],
    };

    setMessages((prev) => [...prev, userMessage, aiResponse]);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <div className="flex-1 container mx-auto px-4 py-6 flex gap-6 max-h-[calc(100vh-5rem)]">
        {/* Left Panel - Selected Papers */}
        <aside className="hidden lg:block w-72 shrink-0">
          <Card className="h-full bg-card border-border">
            <div className="p-4 border-b border-border">
              <h2 className="font-semibold text-foreground flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                Selected Papers ({selectedPapers.length})
              </h2>
            </div>
            <ScrollArea className="h-[calc(100%-4rem)] p-4">
              <div className="space-y-3">
                {selectedPapers.map((paper) => (
                  <div
                    key={paper.id}
                    className="p-3 rounded-lg bg-accent/50 border border-border hover:border-primary/30 transition-colors group"
                  >
                    <h3 className="text-sm font-medium text-foreground line-clamp-2 mb-1">
                      {paper.title}
                    </h3>
                    <p className="text-xs text-muted">
                      {paper.authors[0]} et al., {paper.year}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full mt-2 text-muted hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() =>
                        setSelectedPapers((prev) =>
                          prev.filter((p) => p.id !== paper.id)
                        )
                      }
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      Remove
                    </Button>
                  </div>
                ))}

                <Button
                  variant="outline"
                  className="w-full border-dashed border-border text-muted hover:text-foreground"
                >
                  + Add Papers
                </Button>
              </div>
            </ScrollArea>
          </Card>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col min-w-0">
          <Card className="flex-1 flex flex-col bg-card border-border overflow-hidden">
            {/* Chat Header */}
            <div className="p-4 border-b border-border flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="font-semibold text-foreground">ScholarHub AI</h2>
                <p className="text-sm text-muted">
                  Ask questions about your papers
                </p>
              </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-6">
              <div className="space-y-6 max-w-3xl mx-auto">
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <Bot className="h-12 w-12 text-muted mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-foreground mb-2">
                      Start a conversation
                    </h3>
                    <p className="text-muted max-w-md mx-auto">
                      Ask questions about your research papers. I'll provide
                      answers with citations from your library.
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      role={message.role}
                      content={message.content}
                      citations={
                        message.role === "assistant"
                          ? (message as any).citations
                          : undefined
                      }
                    />
                  ))
                )}
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-4 border-t border-border">
              <div className="max-w-3xl mx-auto">
                <ChatInput onSend={handleSendMessage} />
              </div>
            </div>
          </Card>
        </main>
      </div>
    </div>
  );
};

export default Chat;
