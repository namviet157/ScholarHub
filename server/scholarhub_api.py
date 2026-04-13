"""
ScholarHub FastAPI: GET /document/{mongoObjectId}, POST /chat/rag.

RAG: embed question (sentence-transformers, same as ingestion), retrieve chunks from
Supabase via match_chunks_filtered restricted to arxiv_id(s), then OpenAI gpt-4o-mini.

Env: see .env — SUPABASE_*, OPENAI_API_KEY, MONGO_URL, DATABASE_NAME, DOCUMENT_CONTENTS_COLLECTION,
     DOCUMENTS_API_PORT (default 3001), OPENAI_CHAT_MODEL (default gpt-4o-mini).
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
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
    "I don't have enough indexed content to answer for this paper. "
    "Run the processing pipeline to embed chunks into Supabase (pgvector) for this arXiv id."
)
INSUFFICIENT_MONGO = (
    "I don't have enough document content in the database to answer this question for the selected paper(s). "
    "The full text may not have been ingested into MongoDB yet, or the document ID may be missing."
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
        raw = str((ch or {}).get("text") or "").strip()
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


def retrieve_context_vector(
    arxiv_ids: List[str],
    question: str,
    paper_titles: List[str],
    max_chars: int = 14000,
) -> Tuple[str, List[str]]:
    svc = get_embedding_service()
    q_emb = svc.generator.encode([question])[0]
    blocks: List[str] = []
    citations: List[str] = []
    total = 0
    for i, aid in enumerate(arxiv_ids):
        aid = (aid or "").strip()
        if not aid:
            continue
        hits = svc.index_manager.search_chunks_filtered(
            q_emb,
            k=12,
            filter_paper_ids=[aid],
            min_score=0.0,
        )
        title = paper_titles[i] if i < len(paper_titles) and paper_titles[i] else aid
        chunk_lines: List[str] = []
        for score, meta in hits:
            content = (meta.get("content") or "").strip()
            if not content:
                continue
            chunk_lines.append(f"(similarity {score:.3f}) {content}")
        body = "\n\n".join(chunk_lines)
        if not body:
            continue
        block = f"### Paper: {title} (arXiv:{aid})\n{body}"
        if total + len(block) + 8 > max_chars:
            break
        blocks.append(block)
        total += len(block) + 8
        citations.append(f"{title} ({aid})")
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
                    "the API server (`npm run api:documents` / uvicorn)."
                ),
            },
        )

    arxiv_ids = req.normalized_arxiv_ids()
    mongo_ids = req.normalized_mongo_ids()
    titles = list(req.paper_titles or [])

    context_block = ""
    citations: List[str] = []

    if arxiv_ids:
        context_block, citations = retrieve_context_vector(arxiv_ids, question, titles)
        if not context_block.strip():
            return JSONResponse(
                status_code=200,
                content={
                    "ok": False,
                    "code": "INSUFFICIENT_DATA",
                    "message": INSUFFICIENT_VECTOR,
                },
            )
    elif mongo_ids:
        coll = get_mongo_collection()
        if coll is None:
            return JSONResponse(
                status_code=200,
                content={
                    "ok": False,
                    "code": "INSUFFICIENT_DATA",
                    "message": INSUFFICIENT_MONGO,
                },
            )
        contexts: List[str] = []
        for i, oid in enumerate(mongo_ids):
            doc = coll.find_one({"_id": ObjectId(oid)})
            title = titles[i] if i < len(titles) and titles[i] else (doc.get("paper_id") if doc else oid)
            body = build_context_from_doc(doc, question, 12000) if doc else ""
            if body:
                contexts.append(f"### Paper context ({title})\n{body}")
        context_block = "\n\n---\n\n".join(contexts)
        if not context_block.strip():
            return JSONResponse(
                status_code=200,
                content={
                    "ok": False,
                    "code": "INSUFFICIENT_DATA",
                    "message": INSUFFICIENT_MONGO,
                },
            )
        citations = (
            [t for t in titles if t][: len(mongo_ids)]
            if titles
            else mongo_ids
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "code": "INSUFFICIENT_DATA",
                "message": INSUFFICIENT_VECTOR,
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
