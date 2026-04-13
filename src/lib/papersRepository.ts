import { supabase } from "@/lib/supabase";
import type { Paper, SupabasePaperRow } from "@/types/scholar";
import { paperFromSupabaseOnly } from "@/lib/scholarPaperMappers";

const PAPER_LIST_SELECT = `
  id,
  paper_title,
  abstract,
  arxiv_id,
  mongo_doc_id,
  publication_venue,
  submission_date,
  created_at,
  pdf_url,
  categories,
  paper_authors (
    author_order,
    authors ( name )
  ),
  keywords ( keyword, score )
`;

export async function fetchPapersFromSupabase(): Promise<Paper[]> {
  const { data, error } = await supabase
    .from("papers")
    .select(PAPER_LIST_SELECT)
    .order("mongo_doc_id", { ascending: false, nullsFirst: false }) 
    .order("arxiv_id", { ascending: true });

  if (error) {
    console.error("Error fetching papers:", error.message);
    throw new Error("Could not load papers from Supabase.");
  }

  const rows = (data ?? []) as unknown as SupabasePaperRow[];
  return rows.map((row) => paperFromSupabaseOnly(row));
}

export async function fetchPaperByIdFromSupabase(id: string): Promise<SupabasePaperRow | null> {
  const { data, error } = await supabase
    .from("papers")
    .select(PAPER_LIST_SELECT)
    .eq("id", id)
    .maybeSingle();

  if (error) {
    console.error(`Error fetching paper ${id}:`, error.message);
    return null;
  }
  return data as unknown as SupabasePaperRow | null;
}


/** Normalize arXiv id for matching API rows to catalog papers. */
export function normalizeArxivId(id: string | null | undefined): string {
  if (!id?.trim()) return "";
  return id
    .replace(/^arxiv:/i, "")
    .trim()
    .toLowerCase();
}

/**
 * When semantic search returns ranked arXiv ids, show those papers first (in order),
 * then append keyword matches not already listed. If semantic is unavailable or empty, use keyword-only filter.
 */
export function orderPapersBySemanticThenLexical(
  papers: Paper[],
  q: string,
  semanticArxivIds: string[] | undefined,
  semanticWorked: boolean
): Paper[] {
  const query = q.trim();
  if (!query) return papers;

  if (semanticWorked && semanticArxivIds && semanticArxivIds.length > 0) {
    const byArxiv = new Map<string, Paper>();
    for (const p of papers) {
      const k = normalizeArxivId(p.arxivId);
      if (k && !byArxiv.has(k)) byArxiv.set(k, p);
    }
    const ordered: Paper[] = [];
    const seenIds = new Set<string>();
    for (const raw of semanticArxivIds) {
      const k = normalizeArxivId(raw);
      const p = k ? byArxiv.get(k) : undefined;
      if (p && !seenIds.has(p.id)) {
        ordered.push(p);
        seenIds.add(p.id);
      }
    }
    const lexicalRest = filterPapersByQuery(papers, q).filter((p) => !seenIds.has(p.id));
    return [...ordered, ...lexicalRest];
  }

  return filterPapersByQuery(papers, q);
}

export function filterPapersByQuery(papers: Paper[], q: string): Paper[] {
  const query = q.trim().toLowerCase();
  if (!query) return papers;

  const keywords = query.split(/\s+/);

  return papers.filter((p) => {
    const searchFields = [
      p.title,
      p.abstract,
      p.aiSummary,
      ...(p.authors || []),
      ...(p.keywords || []),
      p.venue,
      p.arxivId,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return keywords.every((word) => searchFields.includes(word));
  });
}

export type PaperListFilters = {
  yearMin: number;
  yearMax: number;
  /** OR match (venue label contains any selected substring) */
  venues: string[];
  /** OR match (any paper category string contains selected substring) */
  categories: string[];
};

export function applyPaperFilters(papers: Paper[], filters: PaperListFilters): Paper[] {
  return papers.filter((p) => {
    if (p.year < filters.yearMin || p.year > filters.yearMax) return false;
    if (filters.venues.length > 0) {
      const v = p.venue.toLowerCase();
      const match = filters.venues.some((f) => v.includes(f.toLowerCase()));
      if (!match) return false;
    }
    if (filters.categories.length > 0) {
      const cats = (p.categories ?? []).map((c) => c.toLowerCase());
      if (cats.length === 0) return false;
      const match = filters.categories.some((f) =>
        cats.some((c) => c.includes(f.toLowerCase()))
      );
      if (!match) return false;
    }
    return true;
  });
}