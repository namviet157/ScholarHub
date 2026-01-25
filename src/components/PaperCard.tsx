import { Bookmark, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Paper } from "@/data/mockPapers";
import { Link } from "react-router-dom";

interface PaperCardProps {
  paper: Paper;
  highlightText?: string;
}

const PaperCard = ({ paper, highlightText }: PaperCardProps) => {
  const highlightMatch = (text: string) => {
    if (!highlightText) return text;
    const regex = new RegExp(`(${highlightText})`, "gi");
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-primary/20 text-foreground px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <Card className="group bg-card border-border hover:border-primary/30 hover:shadow-md transition-all duration-300">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <Link to={`/paper/${paper.id}`} className="block group/title">
              <h3 className="font-semibold text-lg text-foreground mb-2 group-hover/title:text-primary transition-colors line-clamp-2">
                {highlightMatch(paper.title)}
              </h3>
            </Link>
            
            <p className="text-muted text-sm mb-2">
              {paper.authors.slice(0, 3).join(", ")}
              {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
            </p>
            
            <div className="flex items-center gap-3 text-sm text-muted mb-3">
              <span className="font-medium text-primary">{paper.year}</span>
              <span className="w-1 h-1 rounded-full bg-muted" />
              <span>{paper.venue}</span>
              <span className="w-1 h-1 rounded-full bg-muted" />
              <span>{paper.citations.toLocaleString()} citations</span>
            </div>
            
            <p className="text-accent-foreground text-sm leading-relaxed mb-4 line-clamp-3">
              {paper.aiSummary}
            </p>
            
            <div className="flex flex-wrap gap-2">
              {paper.keywords.slice(0, 4).map((keyword) => (
                <Badge
                  key={keyword}
                  variant="secondary"
                  className="bg-accent text-accent-foreground hover:bg-primary/10 hover:text-primary transition-colors cursor-pointer"
                >
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
          
          <div className="flex flex-col gap-2 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="text-muted hover:text-primary hover:bg-primary/10"
            >
              <Bookmark className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted hover:text-primary hover:bg-primary/10"
              asChild
            >
              <Link to={`/paper/${paper.id}`}>
                <ExternalLink className="h-5 w-5" />
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PaperCard;
