import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, UTC
import time

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ARXIV_PAPERS_DIR = Path(__file__).parent.parent / "ArXivPapers"

def safe_insert_author(supabase, data, retries=3):
    for i in range(retries):
        try:
            return supabase.table("authors").upsert(
                data
            ).execute()
        except Exception as e:
            print(f"[WARN] Insert failed (try {i+1}/{retries}): {e}")
            time.sleep(1.5 * (i + 1))
    return None

def get_or_create_author(author_name: str) -> int:
    result = supabase.table("authors").select("id").eq("name", author_name).execute()
    
    if result.data and len(result.data) > 0:
        return result.data[0]["id"]

    result = safe_insert_author(supabase, {
        "name": author_name,
        "created_at": datetime.now(UTC).isoformat()
    })
    
    if result.data and len(result.data) > 0:
        return result.data[0]["id"]
    else:
        raise Exception(f"Failed to create author: {author_name}")


def insert_paper(metadata: Dict) -> Optional[int]:
    arxiv_id = metadata.get("arxiv_id")
    if not arxiv_id:
        return None
    
    result = supabase.table("papers").select("id").eq("arxiv_id", arxiv_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]["id"]
    
    paper_data = {
        "paper_title": metadata.get("paper_title"),
        "abstract": metadata.get("abstract"),
        "arxiv_id": arxiv_id,
        "mongo_doc_id": None,
        "ai_status": "pending",
        "embedding_status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "latest_version": metadata.get("latest_version") if metadata.get("latest_version") else None,
        "revised_dates": metadata.get("revised_dates", []) if metadata.get("revised_dates") else None,
        "publication_venue": metadata.get("publication_venue") if metadata.get("publication_venue") else None,
        "categories": metadata.get("categories", []) if metadata.get("categories") else None,
        "submission_date": metadata.get("submission_date") if metadata.get("submission_date") else None,
        "pdf_url": metadata.get("pdf_url") if metadata.get("pdf_url") else None
    }
    
    try:
        result = supabase.table("papers").insert(paper_data).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return None
    except Exception as e:
        print(f"Error inserting paper {arxiv_id}: {str(e)}")
        return None


def insert_paper_authors(paper_id: int, authors: List[str]):
    if not authors:
        return

    seen_authors = set()
    unique_authors = []
    for name in authors:
        norm_name = name.strip()
        if norm_name and norm_name not in seen_authors:
            seen_authors.add(norm_name)
            unique_authors.append(norm_name)
    
    existing = (
        supabase
        .table("paper_authors")
        .select("author_id")
        .eq("paper_id", paper_id)
        .execute()
    )

    existing_author_ids = {
        row["author_id"] for row in existing.data
    } if existing.data else set()
    
    paper_authors_data = []
    for order, author_name in enumerate(unique_authors, start=1):
        try:
            author_id = get_or_create_author(author_name)
            if author_id in existing_author_ids:
                continue
            paper_authors_data.append({
                "paper_id": paper_id,
                "author_id": author_id,
                "created_at": datetime.now(UTC).isoformat(),
                "author_order": order
            })
        except Exception as e:
            print(f"Error processing author '{author_name}': {str(e)}")
            continue
    
    if paper_authors_data:
        try:
            supabase.table("paper_authors").insert(paper_authors_data).execute()
        except Exception as e:
            print(f"Error inserting paper_authors for paper ID {paper_id}: {str(e)}")


def process_metadata_file(metadata_path: Path) -> bool:
    try:
        with open(metadata_path, 'r', encoding='utf-8-sig') as f:
            metadata = json.load(f)
        
        paper_id = insert_paper(metadata)
        if not paper_id:
            return False
        
        authors = metadata.get("authors", [])
        if authors:
            insert_paper_authors(paper_id, authors)
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {metadata_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error processing {metadata_path}: {str(e)}")
        return False

def main():
    if not ARXIV_PAPERS_DIR.exists():
        print(f"ArXivPapers directory not found: {ARXIV_PAPERS_DIR}")
        return
    
    metadata_files = list(ARXIV_PAPERS_DIR.glob("*/metadata.json"))
    
    if not metadata_files:
        print("No metadata.json files found")
        return
    
    metadata_files.sort()
    
    success_count = 0
    error_count = 0
    
    PAGE_SIZE = 1000
    all_rows = []
    start = 0

    while True:
        resp = (
            supabase
            .table("papers")
            .select("arxiv_id")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )

        if not resp.data:
            break

        all_rows.extend(resp.data)
        start += PAGE_SIZE

    imported_ids = {row["arxiv_id"] for row in all_rows}

    print("Total imported papers:", len(imported_ids))
    metadata_files = [
        path for path in metadata_files
        if path.parent.name not in imported_ids
    ]
    print(f"Processing {len(metadata_files)} papers")

    for i, metadata_path in enumerate(metadata_files, 1):
        folder_name = metadata_path.parent.name
        print(f"[{i}/{len(metadata_files)}] {folder_name}")
        
        if process_metadata_file(metadata_path):
            success_count += 1
        else:
            error_count += 1
    
    print()
    print(f"Summary: {success_count} success, {error_count} errors, {len(metadata_files)} total")


if __name__ == "__main__":
    main()
