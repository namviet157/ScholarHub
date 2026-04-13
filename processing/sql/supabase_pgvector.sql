-- Run in Supabase SQL editor after creating `papers` and `chunks`.
--
-- Expected `public.chunks`: id, paper_id, content, embedding (FK paper_id -> papers.arxiv_id).
-- If you add section_id / chunk_index later, extend the RETURNS TABLE and SELECT lists in
-- match_chunks / match_chunks_filtered to include those columns.
--
-- Embedding dimension must match the model (BGE-base-en-v1.5 => 768). Change vector(768) if needed.

CREATE EXTENSION IF NOT EXISTS vector;

-- Global chunk similarity (inner product; L2-normalized embeddings => score ~ cosine similarity)
CREATE OR REPLACE FUNCTION public.match_chunks(query_embedding vector(768), match_count integer)
RETURNS TABLE (
  id uuid,
  paper_id character varying,
  content text,
  score double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.paper_id,
    c.content,
    (-(c.embedding <#> query_embedding))::double precision AS score
  FROM public.chunks c
  WHERE c.embedding IS NOT NULL
  ORDER BY c.embedding <#> query_embedding
  LIMIT match_count;
$$;

-- Paper-level similarity using papers.embedding
CREATE OR REPLACE FUNCTION public.match_papers(query_embedding vector(768), match_count integer)
RETURNS TABLE (
  arxiv_id character varying,
  paper_title character varying,
  score double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    p.arxiv_id,
    p.paper_title,
    (-(p.embedding <#> query_embedding))::double precision AS score
  FROM public.papers p
  WHERE p.embedding IS NOT NULL
  ORDER BY p.embedding <#> query_embedding
  LIMIT match_count;
$$;

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
  ON public.chunks USING hnsw (embedding vector_ip_ops);

CREATE INDEX IF NOT EXISTS idx_papers_embedding_hnsw
  ON public.papers USING hnsw (embedding vector_ip_ops);

-- Filtered chunk search (paper_id list + minimum inner-product score)
CREATE OR REPLACE FUNCTION public.match_chunks_filtered(
  query_embedding vector(768),
  match_count integer,
  filter_paper_ids text[] DEFAULT NULL,
  min_score double precision DEFAULT 0.0
)
RETURNS TABLE (
  id uuid,
  paper_id character varying,
  content text,
  score double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.paper_id,
    c.content,
    (-(c.embedding <#> query_embedding))::double precision AS score
  FROM public.chunks c
  WHERE c.embedding IS NOT NULL
    AND (-(c.embedding <#> query_embedding))::double precision >= min_score
    AND filter_paper_ids IS NOT NULL
    AND cardinality(filter_paper_ids) > 0
    AND c.paper_id = ANY (filter_paper_ids)
  ORDER BY c.embedding <#> query_embedding
  LIMIT match_count;
$$;
