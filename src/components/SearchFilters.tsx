import { Calendar, User, Tag, Building2 } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { useState } from "react";

const SearchFilters = () => {
  const [yearRange, setYearRange] = useState([2015, 2024]);

  const topics = [
    "Machine Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Deep Learning",
    "Reinforcement Learning",
    "Transformers",
  ];

  const venues = [
    "NeurIPS",
    "ICML",
    "ICLR",
    "ACL",
    "CVPR",
    "arXiv",
  ];

  return (
    <div className="space-y-6">
      {/* Year Range */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Calendar className="h-4 w-4 text-primary" />
          <span>Year Range</span>
        </div>
        <div className="px-2">
          <Slider
            value={yearRange}
            onValueChange={setYearRange}
            min={2000}
            max={2024}
            step={1}
            className="w-full"
          />
          <div className="flex justify-between text-sm text-muted mt-2">
            <span>{yearRange[0]}</span>
            <span>{yearRange[1]}</span>
          </div>
        </div>
      </div>

      {/* Topics */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Tag className="h-4 w-4 text-primary" />
          <span>Topics</span>
        </div>
        <div className="space-y-2">
          {topics.map((topic) => (
            <div key={topic} className="flex items-center space-x-2">
              <Checkbox id={topic} className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary" />
              <Label htmlFor={topic} className="text-sm text-accent-foreground cursor-pointer">
                {topic}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Venues */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Building2 className="h-4 w-4 text-primary" />
          <span>Venue</span>
        </div>
        <div className="space-y-2">
          {venues.map((venue) => (
            <div key={venue} className="flex items-center space-x-2">
              <Checkbox id={venue} className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary" />
              <Label htmlFor={venue} className="text-sm text-accent-foreground cursor-pointer">
                {venue}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Authors */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <User className="h-4 w-4 text-primary" />
          <span>Popular Authors</span>
        </div>
        <div className="space-y-2">
          {["Yann LeCun", "Geoffrey Hinton", "Yoshua Bengio", "Andrew Ng"].map((author) => (
            <div key={author} className="flex items-center space-x-2">
              <Checkbox id={author} className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary" />
              <Label htmlFor={author} className="text-sm text-accent-foreground cursor-pointer">
                {author}
              </Label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchFilters;
