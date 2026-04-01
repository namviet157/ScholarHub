import type { MongoDocumentPayload, Paper, SupabasePaperRow } from "@/types/scholar";

function yearFromRow(row: SupabasePaperRow): number {
  const d = row.submission_date || row.created_at;
  if (!d) return new Date().getFullYear();
  const y = new Date(d).getFullYear();
  return Number.isFinite(y) ? y : new Date().getFullYear();
}

function authorsFromRow(row: SupabasePaperRow): string[] {
  const links = row.paper_authors ?? [];
  const sorted = [...links].sort(
    (a, b) => (a.author_order ?? 999) - (b.author_order ?? 999)
  );
  return sorted
    .map((pa) => pa.authors?.name)
    .filter((n): n is string => Boolean(n?.trim()));
}

function keywordsFromRow(row: SupabasePaperRow): string[] {
  const kws = row.keywords ?? [];
  return [...kws]
    .sort((a, b) => b.score - a.score)
    .map((k) => k.keyword);
}

export function paperFromSupabaseOnly(row: SupabasePaperRow): Paper {
  const abstract = row.abstract?.trim() ?? "";
  const teaser =
    abstract.length > 320 ? `${abstract.slice(0, 317).trimEnd()}…` : abstract;

  return {
    id: row.id,
    title: row.paper_title,
    authors: authorsFromRow(row),
    year: yearFromRow(row),
    venue: row.publication_venue?.trim() || "arXiv",
    abstract,
    aiSummary: teaser,
    keywords: keywordsFromRow(row),
    citations: 0,
    sections: abstract ? [{ title: "Abstract", content: abstract }] : [],
    arxivId: row.arxiv_id,
    mongoDocId: row.mongo_doc_id,
    pdfUrl: row.pdf_url,
    categories: row.categories ?? null,
  };
}

export function sectionsFromMongoDoc(doc: MongoDocumentPayload | null | undefined): { title: string; content: string }[] {
  if (!doc) return [];
  const abstract = doc.abstract?.trim();
  const parts: { title: string; content: string }[] = [];
  if (abstract) {
    parts.push({ title: "Abstract", content: abstract });
  }

  const secList = [...(doc.sections ?? [])].sort((a, b) => a.order - b.order);
  const chunks = doc.chunks ?? [];

  for (const sec of secList) {
    const texts = chunks
      .filter((c) => c.section_id === sec.section_id && c.text?.trim())
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((c) => c.text!.trim());
    const content = texts.join("\n\n");
    if (content) {
      parts.push({ title: sec.title, content });
    }
  }

  if (parts.length === 0 && abstract) {
    return [{ title: "Abstract", content: abstract }];
  }
  return parts;
}

function aiSummaryFromMongo(doc: MongoDocumentPayload): string {
  const s = doc.summaries;
  const text = s?.document_summary?.trim() || s?.abstract_summary?.trim() || "";
  return text;
}

export function mergeMongoIntoPaper(base: Paper, doc: MongoDocumentPayload | null | undefined): Paper {
  if (!doc) return base;

  const fromMongoSummary = aiSummaryFromMongo(doc);
  const sections = sectionsFromMongoDoc(doc);
  const mongoKeywords =
    doc.keywords?.keybert?.map((k) => k.keyword).filter(Boolean) ?? [];

  return {
    ...base,
    abstract: doc.abstract?.trim() || base.abstract,
    aiSummary: fromMongoSummary || base.aiSummary,
    sections: sections.length ? sections : base.sections,
    keywords: mongoKeywords.length ? mongoKeywords : base.keywords,
  };
}
