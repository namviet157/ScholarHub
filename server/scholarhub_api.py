from __future__ import annotations

import importlib.util
import os
import re
import sys
from itertools import zip_longest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load vector_service without importing processing/__init__.py (avoids KeyBERT & pipeline deps).
_vs_path = ROOT / "processing" / "vector_service.py"
_spec = importlib.util.spec_from_file_location("_scholarhub_vector_service", _vs_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load {_vs_path}")
_vector_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vector_mod)
get_embedding_service: Callable[[], Any] = _vector_mod.get_embedding_service

OPENAI_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

INSUFFICIENT_VECTOR = (
    "No vector chunks were retrieved for this paper. "
    "Ensure Supabase `chunks` rows exist with `paper_id` matching this arXiv id (try versioned and unversioned id), "
    "or use MongoDB ingest and pass mongoDocIds from the app."
)
INSUFFICIENT_MONGO = (
    "No usable text chunks were found in MongoDB for this document. "
    "Check DOCUMENT_CONTENTS_COLLECTION and that chunks use a `text` field."
)
INSUFFICIENT_NO_IDS = (
    "This paper has no arXiv id and no MongoDB document id for RAG. "
    "Add an arXiv id in Supabase or link a mongo_doc_id."
)

_mongo_client: Optional[MongoClient] = None
_mongo_collection: Any = None


def _mongo_ready() -> bool:
    return bool(os.getenv("MONGO_URL") and os.getenv("DATABASE_NAME"))


def get_mongo_collection():
    if not _mongo_ready():
        return None
    global _mongo_client, _mongo_collection
    if _mongo_collection is not None:
        return _mongo_collection
    coll_name = os.getenv("DOCUMENT_CONTENTS_COLLECTION", "document_contents")
    _mongo_client = MongoClient(os.getenv("MONGO_URL"))
    _mongo_collection = _mongo_client[os.getenv("DATABASE_NAME")][coll_name]
    return _mongo_collection


def tokenize(s: str) -> List[str]:
    return [
        w
        for w in re.sub(r"[^\w\s]", " ", s.lower()).split()
        if len(w) > 2
    ]


def score_chunk(text: str, q_tokens: List[str]) -> int:
    t = text.lower()
    return sum(1 for w in q_tokens if w in t)


def build_context_from_doc(doc: Dict[str, Any], question: str, max_chars: int = 14000) -> str:
    chunks = doc.get("chunks")
    if not isinstance(chunks, list) or len(chunks) == 0:
        return ""
    q_tokens = tokenize(question)
    scored = []
    for i, ch in enumerate(chunks):
        chd = ch or {}
        raw = str(chd.get("text") or chd.get("content") or "").strip()
        if not raw:
            continue
        scored.append({"i": i, "text": raw, "s": score_chunk(raw, q_tokens)})
    scored.sort(key=lambda x: x["s"], reverse=True)
    parts: List[str] = []
    total = 0
    for x in scored:
        line = f"[chunk {x['i']}] {x['text']}"
        if total + len(line) + 1 > max_chars:
            break
        parts.append(line)
        total += len(line) + 1
    return "\n".join(parts)


def openai_complete(system_prompt: str, user_prompt: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = OpenAI(api_key=key)
    r = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=1200,
    )
    return (r.choices[0].message.content or "").strip()


def _arxiv_norm_for_match(s: str) -> str:
    x = (s or "").strip().lower()
    x = re.sub(r"^arxiv:", "", x)
    x = re.sub(r"\.pdf$", "", x)
    x = re.sub(r"v\d+$", "", x)
    return x


def _arxiv_id_filter_variants(aid: str) -> List[str]:
    raw = (aid or "").strip()
    if not raw:
        return []
    s = re.sub(r"^arxiv:", "", raw, flags=re.I).strip()
    base = re.sub(r"v\d+$", "", s, flags=re.I)
    out: List[str] = []
    for v in (raw, s, base):
        if v and v not in out:
            out.append(v)
    if s != base and base and base not in out:
        out.append(base)
    return out


def _vector_hits_for_arxiv(
    svc: Any,
    q_emb: Any,
    aid: str,
    k: int = 12,
) -> List[Tuple[float, Dict[str, Any]]]:
    variants = _arxiv_id_filter_variants(aid)
    hits: List[Tuple[float, Dict[str, Any]]] = []
    if variants:
        hits = svc.index_manager.search_chunks_filtered(
            q_emb,
            k=k,
            filter_paper_ids=variants,
            min_score=0.0,
        )
    if not hits:
        norm_targets = (
            {_arxiv_norm_for_match(v) for v in variants}
            if variants
            else {_arxiv_norm_for_match(aid)}
        )
        raw = svc.index_manager.search_chunks(q_emb, k=max(k * 4, 48))
        for score, meta in raw:
            pid = str(meta.get("paper_id") or "")
            if _arxiv_norm_for_match(pid) in norm_targets:
                hits.append((score, meta))
            if len(hits) >= k:
                break
    return hits


def _format_vector_block(aid: str, title: str, hits: List[Tuple[float, Dict[str, Any]]]) -> str:
    chunk_lines: List[str] = []
    for score, meta in hits:
        content = (meta.get("content") or "").strip()
        if not content:
            continue
        chunk_lines.append(f"(similarity {score:.3f}) {content}")
    body = "\n\n".join(chunk_lines)
    if not body:
        return ""
    return f"### Paper: {title} (arXiv:{aid})\n{body}"


def assemble_rag_context(
    arxiv_ids: List[str],
    mongo_ids: List[str],
    paper_titles: List[str],
    question: str,
    max_chars: int = 14000,
) -> Tuple[str, List[str]]:
    """Per paper: Supabase vector chunks first, then Mongo for the same slot if vector is empty."""
    svc = get_embedding_service()
    q_emb = svc.generator.encode([question])[0]
    coll = get_mongo_collection()

    blocks: List[str] = []
    citations: List[str] = []
    total = 0

    for i, (aid_raw, mid_raw) in enumerate(zip_longest(arxiv_ids, mongo_ids, fillvalue="")):
        aid = (aid_raw or "").strip()
        mid = str(mid_raw or "").strip()
        mid_ok = bool(mid and re.match(r"^[a-f0-9]{24}$", mid, re.I))

        title = ""
        if i < len(paper_titles) and paper_titles[i]:
            title = str(paper_titles[i]).strip()
        if not title:
            title = aid or (mid if mid_ok else "") or f"Paper {i + 1}"

        part = ""
        cite = ""

        if aid:
            hits = _vector_hits_for_arxiv(svc, q_emb, aid)
            part = _format_vector_block(aid, title, hits)
            cite = f"{title} ({aid})"

        if not part.strip() and mid_ok and coll is not None:
            doc = coll.find_one({"_id": ObjectId(mid)})
            mt = (
                paper_titles[i]
                if i < len(paper_titles) and paper_titles[i]
                else (doc.get("paper_id") if doc else mid)
            )
            body = build_context_from_doc(doc, question, 12000) if doc else ""
            if body:
                part = f"### Paper context ({mt})\n{body}"
                cite = f"{mt} (MongoDB)"

        if not part.strip():
            continue
        if total + len(part) + 8 > max_chars:
            break
        blocks.append(part)
        citations.append(cite)
        total += len(part) + 8

    return "\n\n---\n\n".join(blocks), citations


class RagChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str = ""
    arxiv_id: Optional[str] = Field(None, alias="arxivId")
    arxiv_ids: List[str] = Field(default_factory=list, alias="arxivIds")
    mongo_doc_ids: List[str] = Field(default_factory=list, alias="mongoDocIds")
    paper_titles: List[str] = Field(default_factory=list, alias="paperTitles")

    def normalized_arxiv_ids(self, max_papers: int = 2) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        if self.arxiv_id:
            s = str(self.arxiv_id).strip()
            if s:
                seen.add(s)
                out.append(s)
        for a in self.arxiv_ids:
            s = str(a or "").strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= max_papers:
                break
        return out[:max_papers]

    def normalized_mongo_ids(self, max_papers: int = 2) -> List[str]:
        out: List[str] = []
        for x in self.mongo_doc_ids:
            s = str(x or "").strip()
            if re.match(r"^[a-f0-9]{24}$", s, re.I) and s not in out:
                out.append(s)
            if len(out) >= max_papers:
                break
        return out[:max_papers]


app = FastAPI(title="ScholarHub API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


class SemanticSearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = ""
    limit: int = Field(48, ge=1, le=200)


@app.post("/search/semantic")
def search_semantic(req: SemanticSearchRequest):
    """Embed query and rank papers via Supabase `match_papers` (pgvector on papers.embedding)."""
    q = (req.query or "").strip()
    if not q:
        return JSONResponse(content={"ok": True, "arxivIds": [], "scores": []})

    try:
        svc = get_embedding_service()
        q_emb = svc.generator.encode([q])[0]
        hits = svc.index_manager.search_papers(q_emb, k=int(req.limit))
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "code": "SEMANTIC_UNAVAILABLE",
                "message": str(e)[:800],
                "arxivIds": [],
                "scores": [],
            },
        )

    arxiv_ids: List[str] = []
    scores: List[float] = []
    for score, meta in hits:
        aid = str((meta or {}).get("arxiv_id") or "").strip()
        if not aid:
            continue
        arxiv_ids.append(aid)
        scores.append(float(score))

    return JSONResponse(
        content={
            "ok": True,
            "arxivIds": arxiv_ids,
            "scores": scores,
        }
    )


@app.get("/document/{doc_id}")
def get_document(doc_id: str):
    if not re.match(r"^[a-f0-9]{24}$", doc_id, re.I):
        raise HTTPException(status_code=404, detail="Not found")
    coll = get_mongo_collection()
    if coll is None:
        raise HTTPException(status_code=503, detail="MongoDB not configured")
    try:
        doc = coll.find_one({"_id": ObjectId(doc_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    oid = doc.pop("_id", None)
    out = {**doc, "_id": str(oid) if oid is not None else ""}
    return JSONResponse(content=out)


@app.post("/chat/rag")
def chat_rag(req: RagChatRequest):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    if not os.getenv("OPENAI_API_KEY"):
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "code": "LLM_DISABLED",
                "message": (
                    "The Ask AI service is not configured. Set OPENAI_API_KEY in .env and restart "
                    "the API server (`npm run api` / uvicorn)."
                ),
            },
        )

    arxiv_ids = req.normalized_arxiv_ids()
    mongo_ids = req.normalized_mongo_ids()
    titles = list(req.paper_titles or [])

    context_block = ""
    citations: List[str] = []

    if not arxiv_ids and not mongo_ids:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "code": "INSUFFICIENT_DATA",
                "message": INSUFFICIENT_NO_IDS,
            },
        )

    context_block, citations = assemble_rag_context(arxiv_ids, mongo_ids, titles, question)

    if not context_block.strip() and mongo_ids and get_mongo_collection() is None:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "code": "INSUFFICIENT_DATA",
                "message": INSUFFICIENT_MONGO + " MongoDB is not configured on the server.",
            },
        )

    if not context_block.strip():
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "code": "INSUFFICIENT_DATA",
                "message": (
                    INSUFFICIENT_VECTOR
                    if arxiv_ids
                    else INSUFFICIENT_MONGO
                ),
            },
        )

    system_prompt = """You are a research assistant. Answer ONLY using the CONTEXT below (retrieved excerpts from academic papers).
If the context does not contain enough information, say clearly that you cannot answer from the provided excerpts.
Use clear English. When citing, mention which paper (arXiv id) or passage the idea comes from when possible.
Do not fabricate citations or unseen results."""

    user_prompt = f"CONTEXT:\n{context_block}\n\nQUESTION:\n{question}"

    try:
        answer = openai_complete(system_prompt, user_prompt)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "code": "LLM_ERROR",
                "message": str(e)[:800],
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "answer": answer,
            "citations": citations,
            "arxivIds": arxiv_ids or None,
        },
    )
