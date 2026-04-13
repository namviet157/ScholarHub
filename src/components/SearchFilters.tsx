import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Calendar, Tag, Building2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import type { PaperListFilters } from "@/lib/papersRepository";
import { cn } from "@/lib/utils";

export type SearchFiltersState = PaperListFilters;

type SearchFiltersProps = {
  value: SearchFiltersState;
  onChange: (next: SearchFiltersState) => void;
  venueOptions: string[];
  categoryOptions: string[];
};

const defaultYearMax = () => new Date().getFullYear();

function SectionCard({
  icon: Icon,
  title,
  subtitle,
  children,
  className,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border/80 bg-gradient-to-b from-card to-muted/20 p-4 shadow-sm",
        className
      )}
    >
      <div className="flex items-start gap-3 mb-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0 pt-0.5">
          <h3 className="text-sm font-semibold text-foreground leading-tight">{title}</h3>
          {subtitle ? <p className="text-xs text-muted mt-0.5">{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </div>
  );
}

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
    <div className="space-y-5">
      <SectionCard
        icon={Calendar}
        title="Publication year"
        subtitle="Drag handles to narrow the time range"
      >
        <div className="px-1">
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
            className="w-full [&_[role=slider]]:border-primary [&_[role=slider]]:bg-background"
          />
          <div className="mt-3 flex items-center justify-between gap-2">
            <span className="tabular-nums rounded-lg bg-muted/60 px-2.5 py-1 text-sm font-medium text-foreground">
              {value.yearMin}
            </span>
            <span className="text-xs text-muted">to</span>
            <span className="tabular-nums rounded-lg bg-muted/60 px-2.5 py-1 text-sm font-medium text-foreground">
              {value.yearMax}
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        icon={Building2}
        title="Venue"
        subtitle={`${venueOptions.length} in catalog${value.venues.length ? ` · ${value.venues.length} selected` : ""}`}
      >
        <div
          className="max-h-52 space-y-2 overflow-y-auto rounded-xl border border-border/60 bg-background/50 p-2 pr-1"
          style={{ scrollbarGutter: "stable" }}
        >
          {venueOptions.length === 0 ? (
            <p className="px-2 py-3 text-center text-xs text-muted">No venues in loaded papers.</p>
          ) : (
            venueOptions.map((venue) => (
              <label
                key={venue}
                htmlFor={`venue-${venue}`}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 transition-colors",
                  value.venues.includes(venue) ? "bg-primary/10" : "hover:bg-muted/50"
                )}
              >
                <Checkbox
                  id={`venue-${venue}`}
                  checked={value.venues.includes(venue)}
                  onCheckedChange={() => toggleVenue(venue)}
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                <span className="text-sm leading-snug text-foreground">{venue}</span>
              </label>
            ))
          )}
        </div>
      </SectionCard>

      <SectionCard
        icon={Tag}
        title="Categories"
        subtitle={`${categoryOptions.length} labels${value.categories.length ? ` · ${value.categories.length} selected` : ""}`}
      >
        <div
          className="max-h-52 space-y-2 overflow-y-auto rounded-xl border border-border/60 bg-background/50 p-2 pr-1"
          style={{ scrollbarGutter: "stable" }}
        >
          {categoryOptions.length === 0 ? (
            <p className="px-2 py-3 text-center text-xs text-muted">No categories in loaded papers.</p>
          ) : (
            categoryOptions.map((cat) => (
              <label
                key={cat}
                htmlFor={`cat-${cat}`}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 transition-colors",
                  value.categories.includes(cat) ? "bg-primary/10" : "hover:bg-muted/50"
                )}
              >
                <Checkbox
                  id={`cat-${cat}`}
                  checked={value.categories.includes(cat)}
                  onCheckedChange={() => toggleCategory(cat)}
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                <span className="text-sm leading-snug text-foreground">{cat}</span>
              </label>
            ))
          )}
        </div>
      </SectionCard>
    </div>
  );
}

export default SearchFilters;
