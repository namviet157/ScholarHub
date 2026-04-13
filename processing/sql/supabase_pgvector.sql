-- Run in Supabase SQL editor after creating papers / sections / chunks tables.
-- Assumes pgvector column dimension matches BGE-base (768). Adjust if your column differs.

CREATE EXTENSION IF NOT EXISTS vector;

-- Chunk similarity (inner product; use L2-normalized embeddings)
CREATE OR REPLACE FUNCTION public.match_chunks(query_embedding vector(768), match_count integer)
RETURNS TABLE (
  id uuid,
  paper_id character varying,
  section_id text,
  chunk_index integer,
  content text,
  score double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.paper_id,
    c.section_id,
    c.chunk_index,
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

-- Filtered chunk search (paper_id + minimum inner-product similarity; embeddings L2-normalized => score ~ cosine sim)
CREATE OR REPLACE FUNCTION public.match_chunks_filtered(
  query_embedding vector(768),
  match_count integer,
  filter_paper_ids text[] DEFAULT NULL,
  min_score double precision DEFAULT 0.0
)
RETURNS TABLE (
  id uuid,
  paper_id character varying,
  section_id text,
  chunk_index integer,
  content text,
  score double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.paper_id,
    c.section_id,
    c.chunk_index,
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

-- Optional: lexical candidates for hybrid RAG (requires content indexed for search — add GIN if slow)
CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
  ON public.chunks USING gin (to_tsvector('english', coalesce(content, '')));

CREATE OR REPLACE FUNCTION public.match_chunks_lexical(
  query_text text,
  filter_paper_ids text[],
  match_count integer
)
RETURNS TABLE (
  id uuid,
  paper_id character varying,
  section_id text,
  chunk_index integer,
  content text,
  kw_rank double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.paper_id,
    c.section_id,
    c.chunk_index,
    c.content,
    ts_rank(
      to_tsvector('english', coalesce(c.content, '')),
      plainto_tsquery('english', query_text)
    )::double precision AS kw_rank
  FROM public.chunks c
  WHERE c.content IS NOT NULL
    AND cardinality(filter_paper_ids) > 0
    AND c.paper_id = ANY (filter_paper_ids)
    AND to_tsvector('english', coalesce(c.content, '')) @@ plainto_tsquery('english', query_text)
  ORDER BY kw_rank DESC
  LIMIT match_count;
$$;
