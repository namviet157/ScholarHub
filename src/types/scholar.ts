export interface PaperSection {
  title: string;
  content: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  venue: string;
  abstract: string;
  aiSummary: string;
  keywords: string[];
  citations: number;
  sections: PaperSection[];
  arxivId?: string;
  mongoDocId?: string | null;
  pdfUrl?: string | null;
  categories?: string[] | null;
}

export interface MongoChunk {
  chunk_id?: string;
  section_id?: string;
  text?: string;
  type?: string;
  order?: number;
}

export interface MongoSection {
  section_id: string;
  title: string;
  order: number;
}

export interface MongoDocumentPayload {
  paper_id?: string;
  abstract?: string;
  sections?: MongoSection[];
  chunks?: MongoChunk[];
  summaries?: {
    abstract_summary?: string;
    document_summary?: string;
  };
  keywords?: {
    keybert?: { keyword: string; score?: number; rank?: number }[];
  };
}

type SupabaseAuthorRow = { name: string } | null;

type SupabasePaperAuthorRow = {
  author_order: number | null;
  authors: SupabaseAuthorRow;
};

type SupabaseKeywordRow = {
  keyword: string;
  score: number;
};

export type SupabasePaperRow = {
  id: string;
  paper_title: string;
  abstract: string | null;
  arxiv_id: string;
  mongo_doc_id: string | null;
  publication_venue: string | null;
  submission_date: string | null;
  created_at: string | null;
  pdf_url: string | null;
  categories: string[] | null;
  paper_authors: SupabasePaperAuthorRow[] | null;
  keywords: SupabaseKeywordRow[] | null;
};
