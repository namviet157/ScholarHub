import os
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import Client, create_client

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIM = 768

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def _paper_id_norm(pid: str) -> str:
    x = (pid or "").strip().lower()
    x = re.sub(r"^arxiv:", "", x)
    x = re.sub(r"\.pdf$", "", x)
    x = re.sub(r"v\d+$", "", x)
    return x


class EmbeddingGenerator:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.array([]).reshape(0, EMBEDDING_DIM)

        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            return np.array([]).reshape(0, EMBEDDING_DIM)

        embeddings = self.model.encode(
            non_empty_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings


def _get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set (use service_role key server-side)."
        )
    return create_client(url, key)


class SupabaseVectorManager:
    """
    Stores chunk embeddings and paper-level embedding in Supabase (pgvector).
    Schema: papers.embedding, chunks (paper_id, content, embedding).
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client or _get_supabase()
        self._insert_batch_size = int(os.getenv("SUPABASE_VECTOR_BATCH_SIZE", "100"))

    def clear_paper(self, paper_id: str) -> None:
        """Remove chunks and clear papers.embedding for this arxiv_id before re-ingesting."""
        self._client.table("chunks").delete().eq("paper_id", paper_id).execute()
        self._client.table("papers").update({"embedding": None}).eq("arxiv_id", paper_id).execute()

    def add_chunk_embeddings(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        if len(metadata) == 0:
            return
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata must have the same length")

        rows: List[Dict[str, Any]] = []
        for i, meta in enumerate(metadata):
            full_text = (meta.get("content") or "").strip()
            if not full_text:
                continue
            
            vec = embeddings[i].astype(float)
            rows.append(
                {
                    "paper_id": meta["paper_id"],
                    "content": full_text, # Chỉ lưu full_text và ID theo schema mới
                    "embedding": vec.tolist(),
                }
            )
        self._insert_batches("chunks", rows)

    def _insert_batches(self, table: str, rows: List[Dict[str, Any]]) -> None:
        b = max(1, self._insert_batch_size)
        for i in range(0, len(rows), b):
            batch = rows[i : i + b]
            self._client.table(table).insert(batch).execute()

    def set_paper_embedding(self, arxiv_id: str, embedding: np.ndarray) -> None:
        if not arxiv_id:
            return
        vec = embedding.reshape(-1).astype(float)
        if vec.size != EMBEDDING_DIM:
            raise ValueError(f"Paper embedding dim {vec.size} != EMBEDDING_DIM {EMBEDDING_DIM}")
        self._client.table("papers").update({"embedding": vec.tolist()}).eq("arxiv_id", arxiv_id).execute()

    def search_chunks(
        self, query_embedding: np.ndarray, k: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        q = query_embedding.reshape(1, -1)[0]
        res = self._client.rpc(
            "match_chunks",
            {"query_embedding": q.tolist(), "match_count": k},
        ).execute()
        
        data = res.data or []
        results: List[Tuple[float, Dict[str, Any]]] = []
        for row in data:
            meta = {
                "chunk_id": row.get("id"),
                "paper_id": row.get("paper_id"),
                "content": row.get("content") or "",
            }
            results.append((float(row.get("score", 0.0)), meta))
        return results

    def search_chunks_filtered(
        self,
        query_embedding: np.ndarray,
        k: int,
        filter_paper_ids: List[str],
        min_score: float = 0.0,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """pgvector search restricted to paper_ids with similarity floor. Falls back to match_chunks + Python filter if RPC missing."""
        q = query_embedding.reshape(1, -1)[0].tolist()
        if not filter_paper_ids:
            return []
        try:
            res = self._client.rpc(
                "match_chunks_filtered",
                {
                    "query_embedding": q,
                    "match_count": k,
                    "filter_paper_ids": filter_paper_ids,
                    "min_score": float(min_score),
                },
            ).execute()
        except Exception:
            res = self._client.rpc(
                "match_chunks",
                {"query_embedding": q, "match_count": max(k * 4, 64)},
            ).execute()
        allowed_raw = set(filter_paper_ids)
        allowed_norm = {_paper_id_norm(x) for x in filter_paper_ids}
        data = res.data or []
        results: List[Tuple[float, Dict[str, Any]]] = []
        for row in data:
            score = float(row.get("score", 0.0))
            if score < min_score:
                continue
            pid = str(row.get("paper_id") or "")
            if pid not in allowed_raw and _paper_id_norm(pid) not in allowed_norm:
                continue
            meta = {
                "chunk_id": row.get("id"),
                "paper_id": row.get("paper_id"),
                "content": row.get("content") or "",
            }
            results.append((score, meta))
        return results

    def search_papers(
        self, query_embedding: np.ndarray, k: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        q = query_embedding.reshape(1, -1)[0].tolist()
        try:
            res = self._client.rpc(
                "match_papers",
                {"query_embedding": q, "match_count": k},
            ).execute()
            
            if res.data:
                out = []
                for row in res.data:
                    out.append((
                        float(row.get("score", 0.0)),
                        {
                            "arxiv_id": str(row.get("arxiv_id") or ""),
                            "paper_title": row.get("paper_title") or "",
                        },
                    ))
                return out
        except Exception as e:
            print(f"RPC match_papers failed: {e}")
            return []

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if end < len(text):
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)

            if break_point > chunk_size * 0.5:
                chunk = chunk[: break_point + 1]
                end = start + break_point + 1

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap

    return chunks


def _paper_text_for_embedding(paper_data: Dict[str, Any]) -> str:
    summaries = paper_data.get("summaries") or {}
    main_body = summaries.get("document_summary") or ""
    
    if not main_body:
        abs_text = paper_data.get("abstract") or ""
        abs_sum = summaries.get("abstract_summary") or ""
        main_body = abs_text if len(abs_text) >= len(abs_sum) else abs_sum

    parts = [
        paper_data.get("paper_title") or "",
        main_body
    ]
    return " ".join(p.strip() for p in parts if p and str(p).strip()).strip()


class PaperEmbeddingService:
    def __init__(self):
        self.generator = EmbeddingGenerator()
        self.index_manager = SupabaseVectorManager()

    def generate_chunk_embeddings(
        self, sections: List[Dict[str, Any]], paper_id: str
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        embeddings_list = []
        metadata_list = []

        for section in sections:
            section_title = section.get("title", "")
            
            text_parts = []
            for item in section.get("content", []):
                if item.get("type") == "paragraph":
                    text_parts.append(item.get("text", ""))
                elif item.get("type") == "equation":
                    text_parts.append(item.get("text", ""))

            section_text = " ".join(text_parts)

            if not section_text.strip():
                continue

            chunks = chunk_text(section_text)

            for chunk in chunks:
                if not chunk.strip():
                    continue

                chunk_with_context = f"{section_title}: {chunk}" if section_title else chunk

                embedding = self.generator.encode([chunk_with_context])[0]
                embeddings_list.append(embedding)

                # Lưu chunk_with_context thay vì chunk trơn để LLM đọc tốt hơn
                metadata_list.append(
                    {
                        "paper_id": paper_id,
                        "content": chunk_with_context, 
                    }
                )

        if not embeddings_list:
            return np.array([]).reshape(0, EMBEDDING_DIM), []

        embeddings = np.array(embeddings_list)
        return embeddings, metadata_list

    def process_paper(self, paper_data: Dict[str, Any], sections: List[Dict[str, Any]]) -> bool:
        try:
            paper_id = paper_data.get("arxiv_id") or paper_data.get("paper_id")
            if not paper_id:
                print("  Error: Missing paper_id")
                return False

            print(f"  Generating embeddings for {paper_id}...")

            self.index_manager.clear_paper(paper_id)

            # Đã gỡ bỏ phần xử lý Section Metadata

            chunk_embeddings, chunk_metadata = self.generate_chunk_embeddings(sections, paper_id)
            if len(chunk_embeddings) > 0:
                self.index_manager.add_chunk_embeddings(chunk_embeddings, chunk_metadata)
                print(f"    Upserted {len(chunk_embeddings)} chunks to Supabase")

            paper_vec_text = _paper_text_for_embedding(paper_data)
            if paper_vec_text:
                paper_emb = self.generator.encode([paper_vec_text])[0]
                self.index_manager.set_paper_embedding(paper_id, paper_emb)
                print(f"    Updated papers.embedding for {paper_id}")

            return True

        except Exception as e:
            print(f"  Error generating embeddings: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search(self, query: str, level: str = "chunk", k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.generator.encode([query])[0]

        if level == "paper":
            results = self.index_manager.search_papers(query_embedding, k)
        elif level == "chunk":
            results = self.index_manager.search_chunks(query_embedding, k)
        elif level == "section":
            raise ValueError("Section-level search has been deprecated. Sections are only stored in MongoDB.")
        else:
            raise ValueError(f"Invalid level: {level}. Must be 'paper' or 'chunk'")

        return [{"score": float(score), "metadata": metadata} for score, metadata in results]


_embedding_service: Optional[PaperEmbeddingService] = None

def get_embedding_service() -> PaperEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = PaperEmbeddingService()
    return _embedding_service