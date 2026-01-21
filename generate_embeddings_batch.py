"""
Batch script to generate embeddings for existing papers in MongoDB.
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pathlib import Path
from processing.embeddings import get_embedding_service
from supabase import create_client, Client
from typing import List, Dict, Any

load_dotenv()

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("DOCUMENT_CONTENTS_COLLECTION")

if not MONGO_URL or not DATABASE_NAME or not COLLECTION_NAME:
    raise ValueError("MONGO_URL, DATABASE_NAME, and DOCUMENT_CONTENTS_COLLECTION must be set")

client = MongoClient(MONGO_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None


def update_supabase_embedding_status(paper_id: str, status: str):
    """Update embedding status in Supabase."""
    if not supabase:
        return False
    
    try:
        # Find paper by arxiv_id
        result = supabase.table("papers").select("id").eq("arxiv_id", paper_id).execute()
        if result.data and len(result.data) > 0:
            supabase_paper_id = result.data[0]["id"]
            supabase.table("papers").update({
                "embedding_status": status
            }).eq("id", supabase_paper_id).execute()
            return True
    except Exception as e:
        print(f"  Error updating Supabase status: {e}")
    
    return False


def process_paper(paper_doc: Dict[str, Any], embedding_service) -> bool:
    """Process a single paper to generate embeddings."""
    paper_id = paper_doc.get("paper_id")
    if not paper_id:
        return False
    
    print(f"\nProcessing {paper_id}...")
    
    # Get paper data from Supabase
    paper_title = ""
    abstract = ""
    
    if supabase:
        try:
            result = supabase.table("papers").select("paper_title, abstract").eq("arxiv_id", paper_id).execute()
            if result.data and len(result.data) > 0:
                paper_title = result.data[0].get("paper_title", "")
                abstract = result.data[0].get("abstract", "")
        except Exception as e:
            print(f"  Warning: Could not fetch Supabase data: {e}")
    
    # Get sections and chunks
    sections = paper_doc.get("sections", [])
    chunks = paper_doc.get("chunks", [])
    from processing.import_to_mongodb import reconstruct_sections_with_content, reconstruct_full_text
    
    # Reconstruct sections with content from chunks for embeddings compatibility
    sections_with_content = reconstruct_sections_with_content(sections, chunks)
    
    # Reconstruct full_text from chunks (new format doesn't store it)
    full_text = paper_doc.get("full_text", "")
    if not full_text:
        full_text = reconstruct_full_text(chunks, abstract)
    
    # Prepare paper data
    paper_data = {
        'arxiv_id': paper_id,
        'paper_title': paper_title,
        'abstract': abstract,
        'full_text': full_text,
        'summaries': paper_doc.get("summaries", {})  # Include summaries if available
    }
    
    # Generate embeddings using sections with reconstructed content
    try:
        if embedding_service.process_paper(paper_data, sections_with_content):
            update_supabase_embedding_status(paper_id, "completed")
            print(f"  ✓ Generated embeddings for {paper_id}")
            return True
        else:
            update_supabase_embedding_status(paper_id, "failed")
            print(f"  ✗ Failed to generate embeddings for {paper_id}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        update_supabase_embedding_status(paper_id, "failed")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Generate embeddings for all papers in MongoDB."""
    print("="*60)
    print("Batch Embedding Generation")
    print("="*60)
    
    # Get all papers
    papers = list(collection.find({}))
    total_papers = len(papers)
    
    print(f"\nFound {total_papers} papers in MongoDB")
    
    if total_papers == 0:
        print("No papers to process.")
        return
    
    # Initialize embedding service
    print("\nInitializing embedding service...")
    embedding_service = get_embedding_service()
    
    # Process papers
    success_count = 0
    fail_count = 0
    
    for i, paper_doc in enumerate(papers, 1):
        print(f"\n[{i}/{total_papers}]", end="")
        if process_paper(paper_doc, embedding_service):
            success_count += 1
        else:
            fail_count += 1
        
        # Save periodically (every 10 papers)
        if i % 10 == 0:
            print(f"\n  Saving embeddings...")
            embedding_service.save()
    
    # Final save
    print(f"\n\nSaving all embeddings...")
    embedding_service.save()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total papers: {total_papers}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print("="*60)


if __name__ == "__main__":
    main()
