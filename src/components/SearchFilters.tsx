import { Calendar, Tag, Building2 } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import type { PaperListFilters } from "@/lib/papersRepository";

export type SearchFiltersState = PaperListFilters;

type SearchFiltersProps = {
  value: SearchFiltersState;
  onChange: (next: SearchFiltersState) => void;
  venueOptions: string[];
  categoryOptions: string[];
};

const defaultYearMax = () => new Date().getFullYear();

function SearchFilters({ value, onChange, venueOptions, categoryOptions }: SearchFiltersProps) {
  const yearMaxCap = Math.max(defaultYearMax(), value.yearMax);

  const toggleVenue = (venue: string) => {
    const set = new Set(value.venues);
    if (set.has(venue)) set.delete(venue);
    else set.add(venue);
    onChange({ ...value, venues: [...set] });
  };

  const toggleCategory = (cat: string) => {
    const set = new Set(value.categories);
    if (set.has(cat)) set.delete(cat);
    else set.add(cat);
    onChange({ ...value, categories: [...set] });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Calendar className="h-4 w-4 text-primary" />
          <span>Year range</span>
        </div>
        <div className="px-2">
          <Slider
            value={[value.yearMin, value.yearMax]}
            onValueChange={(v) =>
              onChange({
                ...value,
                yearMin: v[0] ?? value.yearMin,
                yearMax: v[1] ?? value.yearMax,
              })
            }
            min={1990}
            max={yearMaxCap}
            step={1}
            className="w-full"
          />
          <div className="flex justify-between text-sm text-muted mt-2">
            <span>{value.yearMin}</span>
            <span>{value.yearMax}</span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Building2 className="h-4 w-4 text-primary" />
          <span>Venue</span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {venueOptions.length === 0 ? (
            <p className="text-xs text-muted">No venues in loaded papers.</p>
          ) : (
            venueOptions.map((venue) => (
              <div key={venue} className="flex items-center space-x-2">
                <Checkbox
                  id={`venue-${venue}`}
                  checked={value.venues.includes(venue)}
                  onCheckedChange={() => toggleVenue(venue)}
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                <Label htmlFor={`venue-${venue}`} className="text-sm text-accent-foreground cursor-pointer">
                  {venue}
                </Label>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Tag className="h-4 w-4 text-primary" />
          <span>Categories (arXiv / tags)</span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {categoryOptions.length === 0 ? (
            <p className="text-xs text-muted">No categories in loaded papers.</p>
          ) : (
            categoryOptions.map((cat) => (
              <div key={cat} className="flex items-center space-x-2">
                <Checkbox
                  id={`cat-${cat}`}
                  checked={value.categories.includes(cat)}
                  onCheckedChange={() => toggleCategory(cat)}
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                <Label htmlFor={`cat-${cat}`} className="text-sm text-accent-foreground cursor-pointer">
                  {cat}
                </Label>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default SearchFilters;
