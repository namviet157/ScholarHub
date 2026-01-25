import { Library, Bookmark, Clock, MessageSquare, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import Header from "@/components/Header";
import PaperCard from "@/components/PaperCard";
import { mockPapers } from "@/data/mockPapers";

const Dashboard = () => {
  const recentQuestions = [
    {
      id: "1",
      question: "What is the main contribution of the Transformer paper?",
      answer: "The Transformer introduces self-attention mechanisms...",
      timestamp: "2 hours ago",
    },
    {
      id: "2",
      question: "How does BERT differ from GPT?",
      answer: "BERT uses bidirectional training while GPT is unidirectional...",
      timestamp: "1 day ago",
    },
    {
      id: "3",
      question: "Explain the scaling laws for language models",
      answer: "Scaling laws describe power-law relationships between...",
      timestamp: "3 days ago",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Welcome back, Researcher
          </h1>
          <p className="text-muted">
            Continue your research where you left off
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { icon: Library, label: "Papers", value: "24" },
            { icon: Bookmark, label: "Bookmarks", value: "12" },
            { icon: Clock, label: "Read This Week", value: "8" },
            { icon: MessageSquare, label: "Questions Asked", value: "45" },
          ].map((stat) => (
            <Card key={stat.label} className="bg-card border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <stat.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">
                    {stat.value}
                  </div>
                  <div className="text-sm text-muted">{stat.label}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="library" className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <TabsList className="bg-card border border-border">
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
                />
              </div>
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                <Plus className="h-4 w-4 mr-2" />
                Add Paper
              </Button>
            </div>
          </div>

          <TabsContent value="library" className="space-y-4">
            {mockPapers.slice(0, 4).map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </TabsContent>

          <TabsContent value="bookmarks" className="space-y-4">
            {mockPapers.slice(1, 3).map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            {mockPapers.slice(2, 5).map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </TabsContent>

          <TabsContent value="questions">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-foreground">Recent Questions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {recentQuestions.map((q) => (
                  <div
                    key={q.id}
                    className="p-4 rounded-lg bg-accent/50 border border-border hover:border-primary/30 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h4 className="font-medium text-foreground mb-1">
                          {q.question}
                        </h4>
                        <p className="text-sm text-muted line-clamp-1">
                          {q.answer}
                        </p>
                      </div>
                      <span className="text-xs text-muted shrink-0">
                        {q.timestamp}
                      </span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
