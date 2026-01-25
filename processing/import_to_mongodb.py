from pymongo import MongoClient
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from pathlib import Path
import json
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Tuple
import re
from embeddings import get_embedding_service
from summarization import get_summarizer
from keywords_extraction import get_keyword_extractor

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("DOCUMENT_CONTENTS_COLLECTION")

if not MONGO_URL or not DATABASE_NAME or not COLLECTION_NAME:
    raise ValueError("MONGO_URL, DATABASE_NAME, and DOCUMENT_CONTENTS_COLLECTION must be set in .env file")

client = MongoClient(MONGO_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

ARXIV_PAPERS_DIR = Path(__file__).parent.parent / "ArXivPapers"

SECTION_PATTERNS = [
    (r'\\section\*?\{([^}]*)\}', 'section'),
    (r'\\subsection\*?\{([^}]*)\}', 'subsection'),
    (r'\\subsubsection\*?\{([^}]*)\}', 'subsubsection'),
    (r'\\chapter\*?\{([^}]*)\}', 'chapter'),
]

SECTION_MAPPING = {
    'introduction': 'intro',
    'related work': 'related',
    'methodology': 'method',
    'method': 'method',
    'experiments': 'experiments',
    'results': 'results',
    'discussion': 'discussion',
    'conclusion': 'conclusion',
    'conclusions': 'conclusion',
    'acknowledgments': 'acknowledgments',
    'acknowledgement': 'acknowledgments',
    'references': 'references',
    'bibliography': 'references',
    'appendix': 'appendix',
}


def normalize_section_id(title: str) -> str:
    title_lower = title.lower().strip()
    
    for key, section_id in SECTION_MAPPING.items():
        if key in title_lower:
            return section_id
    
    section_id = re.sub(r'[^a-z0-9]+', '_', title_lower)
    section_id = re.sub(r'_+', '_', section_id).strip('_')
    return section_id[:50]


def reconstruct_sections_with_content(sections: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks_by_section = {}
    for chunk in chunks:
        section_id = chunk.get('section_id', '')
        if section_id not in chunks_by_section:
            chunks_by_section[section_id] = []
        chunks_by_section[section_id].append(chunk)
    
    for section_id in chunks_by_section:
        chunks_by_section[section_id].sort(key=lambda x: x.get('order', 0))
    
    reconstructed = []
    for section in sections:
        section_id = section.get('section_id', '')
        section_chunks = chunks_by_section.get(section_id, [])
        
        content = []
        for chunk in section_chunks:
            chunk_type = chunk.get('type', 'paragraph')
            text = chunk.get('text', '')
            
            if chunk_type == 'paragraph':
                content.append({
                    'type': 'paragraph',
                    'text': text,
                    'order': chunk.get('order', 0)
                })
            elif chunk_type == 'equation':
                content.append({
                    'type': 'equation',
                    'text': text,
                    'order': chunk.get('order', 0)
                })
        
        reconstructed.append({
            'section_id': section_id,
            'title': section.get('title', ''),
            'order': section.get('order', 0),
            'content': content
        })
    
    return reconstructed


def reconstruct_full_text(chunks: List[Dict[str, Any]], abstract: str = "") -> str:
    text_parts = [abstract] if abstract else []
    
    sorted_chunks = sorted(chunks, key=lambda x: x.get('order', 0))
    
    for chunk in sorted_chunks:
        text = chunk.get('text', '')
        if text:
            text_parts.append(text)
    
    return ' '.join(text_parts)


def extract_section_title(element_content: str) -> Optional[str]:
    for pattern, _ in SECTION_PATTERNS:
        match = re.search(pattern, element_content)
        if match:
            return match.group(1)
    return None


def extract_latex_equation(element_content: str) -> Optional[str]:
    equation_match = re.search(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', element_content, re.DOTALL)
    if equation_match:
        return equation_match.group(1).strip()
    
    dollar_match = re.search(r'\$\$(.*?)\$\$', element_content, re.DOTALL)
    if dollar_match:
        return dollar_match.group(1).strip()
    
    inline_match = re.search(r'\$([^$]+)\$', element_content)
    if inline_match:
        return inline_match.group(1).strip()
    
    return None


def is_equation(element_content: str) -> bool:
    return (
        '\\begin{equation' in element_content or
        '\\end{equation' in element_content or
        '$$' in element_content or
        (element_content.count('$') >= 2 and '\\' in element_content)
    )


def infer_node_type(element_content: str) -> str:
    if '\\document' in element_content.lower():
        return 'DOCUMENT'
    elif '\\abstract' in element_content.lower():
        return 'CHAPTER'
    elif re.search(r'\\chapter\*?\{', element_content):
        return 'CHAPTER'
    elif re.search(r'\\section\*?\{', element_content):
        return 'SECTION'
    elif re.search(r'\\subsection\*?\{', element_content):
        return 'SUBSECTION'
    elif re.search(r'\\subsubsection\*?\{', element_content):
        return 'SUBSUBSECTION'
    elif re.search(r'\\paragraph\*?\{', element_content):
        return 'PARAGRAPH'
    elif re.search(r'\\subparagraph\*?\{', element_content):
        return 'SUBPARAGRAPH'
    elif '\\begin{figure' in element_content or '\\includegraphics' in element_content:
        return 'FIGURE'
    elif '\\begin{table' in element_content:
        return 'TABLE'
    elif '\\begin{equation' in element_content or '$$' in element_content:
        return 'BLOCK_FORMULA'
    else:
        return 'PARAGRAPH'

def is_meaningful_content(text: str, node_type: str = 'PARAGRAPH') -> bool:
    if not text or len(text.strip()) == 0:
        return False
    
    if node_type in ['EQUATION', 'FORMULA']:
        return len(text) > 3
    
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    if len(words) < 2:
        return False
    
    return len(text) > 15

def parse_hierarchy_to_chunks(
    elements: Dict[str, str],
    hierarchy: Dict[str, Dict[str, str]],
    sections_metadata: List[Dict[str, Any]],
    abstract: str = ""
) -> List[Dict[str, Any]]:
    chunks = []
    chunk_order = 0
    
    if abstract and abstract.strip():
        chunk_id = f"abstract_{chunk_order}"
        chunks.append({
            'chunk_id': chunk_id,
            'section_id': 'abstract',
            'section_order': 0,
            'text': abstract.strip(),
            'type': 'paragraph',
            'order': chunk_order
        })
        chunk_order += 1
    
    root_id = None
    for elem_id, content in elements.items():
        if '\\document' in content.lower() or content.strip() == "\\document{Document}":
            root_id = elem_id
            break
    
    if not root_id and hierarchy:
        version_key = list(hierarchy.keys())[-1]
        version_hierarchy = hierarchy[version_key]
        all_children = set(version_hierarchy.keys())
        all_parents = set(version_hierarchy.values())
        potential_roots = all_parents - all_children
        if potential_roots:
            root_id = list(potential_roots)[0]
    
    if not root_id:
        return chunks
    
    version_key = list(hierarchy.keys())[-1] if hierarchy else None
    if not version_key:
        return chunks
    
    version_hierarchy = hierarchy[version_key]
    children_map = {}
    for child_id, parent_id in version_hierarchy.items():
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(child_id)
    
    for section_info in sections_metadata:
        section_id = section_info['section_id']
        section_order = section_info['order']
        section_title = section_info['title']
        
        section_elem_id = None
        root_children = children_map.get(root_id, [])
        
        for child_id in root_children:
            content = elements.get(child_id, '')
            if '\\abstract' in content.lower():
                continue
            extracted_title = extract_section_title(content)
            if extracted_title == section_title:
                section_elem_id = child_id
                break
        
        if not section_elem_id:
            continue
        
        def collect_content(elem_id: str, visited: set, depth: int = 0) -> List[Dict[str, Any]]:
            if elem_id in visited or depth > 10:
                return []
            visited.add(elem_id)
            
            content_list = []
            children = children_map.get(elem_id, [])
            
            for child_id in children:
                child_content = elements.get(child_id, '')
                is_subsection = any(re.search(pattern, child_content) for pattern, _ in SECTION_PATTERNS)
                
                if is_subsection:
                    sub_content = collect_content(child_id, visited, depth + 1)
                    content_list.extend(sub_content)
                else:
                    if is_equation(child_content):
                        latex = extract_latex_equation(child_content)
                        if latex:
                            content_list.append({
                                "type": "equation",
                                "text": latex
                            })
                    else:
                        if child_content and child_content.strip():
                            text = child_content.strip()
                            if is_meaningful_content(text):
                                content_list.append({
                                    "type": "paragraph",
                                    "text": text
                                })
            
            return content_list
        
        section_content = collect_content(section_elem_id, set())
        
        section_chunk_idx = 0
        for item in section_content:
            item_type = item.get('type', 'paragraph')
            text = item.get('text', '').strip()
            
            if text and len(text) > 10:
                chunk_id = f"{section_id}_{section_chunk_idx}"
                chunks.append({
                    'chunk_id': chunk_id,
                    'section_id': section_id,
                    'section_order': section_order,
                    'text': text,
                    'type': item_type,
                    'order': chunk_order
                })
                chunk_order += 1
                section_chunk_idx += 1
    
    return chunks


def parse_hierarchy_to_sections(
    elements: Dict[str, str],
    hierarchy: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    sections = []
    
    root_id = None
    for elem_id, content in elements.items():
        if '\\document' in content.lower() or content.strip() == "\\document{Document}":
            root_id = elem_id
            break
    
    if not root_id and hierarchy:
        version_key = list(hierarchy.keys())[-1]
        version_hierarchy = hierarchy[version_key]
        
        all_children = set(version_hierarchy.keys())
        all_parents = set(version_hierarchy.values())
        
        potential_roots = all_parents - all_children
        if potential_roots:
            root_id = list(potential_roots)[0]
    
    if not root_id:
        return sections
    
    version_key = list(hierarchy.keys())[-1] if hierarchy else None
    if not version_key:
        return sections
    
    version_hierarchy = hierarchy[version_key]
    
    children_map = {}  # parent_id -> [child_ids]
    for child_id, parent_id in version_hierarchy.items():
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(child_id)
    
    section_elements = []
    root_children = children_map.get(root_id, [])
    
    for child_id in root_children:
        content = elements.get(child_id, '')
        
        if '\\abstract' in content.lower():
            continue
        
        section_title = extract_section_title(content)
        if section_title:
            section_elements.append({
                'elem_id': child_id,
                'title': section_title
            })
    
    section_elements.sort(key=lambda x: root_children.index(x['elem_id']) if x['elem_id'] in root_children else 999999)
    
    for idx, section_info in enumerate(section_elements):
        section_title = section_info['title']
        section_id = normalize_section_id(section_title)
        
        sections.append({
            'section_id': section_id,
            'title': section_title,
            'order': idx + 1
        })
    
    return sections

def get_paper_from_supabase(arxiv_id: str) -> Optional[Dict[str, Any]]:
    try:
        result = supabase.table("papers").select("*").eq("arxiv_id", arxiv_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error querying Supabase for {arxiv_id}: {str(e)}")
        return None


def update_supabase_mongo_doc_id(paper_id: int, mongo_doc_id: str):
    try:
        supabase.table("papers").update({
            "mongo_doc_id": mongo_doc_id
        }).eq("id", paper_id).execute()
        return True
    except Exception as e:
        print(f"Error updating Supabase for paper_id {paper_id}: {str(e)}")
        return False


def update_supabase_embedding_status(paper_id: int, status: str):
    try:
        supabase.table("papers").update({
            "embedding_status": status
        }).eq("id", paper_id).execute()
        return True
    except Exception as e:
        print(f"Error updating embedding status for paper_id {paper_id}: {str(e)}")
        return False


def save_keywords_to_supabase(paper_id: int, keywords_data: Dict[str, Any]) -> bool:
    try:
        supabase.table("keywords").delete().eq("paper_id", paper_id).execute()
        
        keywords_to_insert = []
        
        for kw in keywords_data.get('keybert', []):
            keywords_to_insert.append({
                'paper_id': paper_id,
                'keyword': kw['keyword'],
                'score': kw['score'],
                'extraction_method': 'keybert',
            })
        
        if keywords_to_insert:
            batch_size = 100
            for i in range(0, len(keywords_to_insert), batch_size):
                batch = keywords_to_insert[i:i + batch_size]
                supabase.table("keywords").insert(batch).execute()
            
            return True
        return False
        
    except Exception as e:
        print(f"Error saving keywords to Supabase for paper_id {paper_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def process_paper_json(json_path: Path) -> bool:
    try:
        paper_id = json_path.stem
        arxiv_id = paper_id
        
        print(f"Processing {paper_id}...")
        
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        
        elements = data.get('elements', {})
        hierarchy = data.get('hierarchy', {})
        
        if not elements or not hierarchy:
            print(f"  Skipping {paper_id}: missing elements or hierarchy")
            return False
        
        sections = parse_hierarchy_to_sections(elements, hierarchy)
        
        if not sections:
            print(f"  Skipping {paper_id}: no sections found")
            return False
        
        paper_data = get_paper_from_supabase(arxiv_id)
        
        if not paper_data:
            print(f"  Warning: Paper {arxiv_id} not found in Supabase, skipping")
            return False
        
        abstract = paper_data.get('abstract', '')
        supabase_paper_id = paper_data.get('id')
        version_key = paper_data.get('latest_version')
        
        chunks = parse_hierarchy_to_chunks(elements, hierarchy, sections, abstract)
        
        total_sections = len(sections)
        total_chunks = len(chunks)
        
        word_count = 0
        for chunk in chunks:
            if chunk.get('text'):
                word_count += len(chunk['text'].split())
        
        summaries = {}
        try:
            summarizer = get_summarizer()
            full_text_body_only = reconstruct_full_text(chunks, "")
            
            summary_result = summarizer.summarize_paper(
                abstract=abstract,
                full_text=full_text_body_only,
                generate_abstract_summary=True,
                generate_document_summary=True
            )
            summaries = {
                'abstract_summary': summary_result.get('abstract_summary'),
                'document_summary': summary_result.get('document_summary')
            }
            print(f"  Generated summaries for {paper_id}")
        except Exception as e:
            print(f"  Warning: Failed to generate summaries for {paper_id}: {e}")
            import traceback
            traceback.print_exc()
        
        keywords = {}
        try:
            keyword_extractor = get_keyword_extractor()
            full_text = reconstruct_full_text(chunks, abstract)
            paper_title = paper_data.get('paper_title', '')
            
            keybert_keywords = keyword_extractor.extract_from_paper(
                abstract=abstract,
                full_text=full_text,
                title=paper_title,
                top_n=10,
                ngram_range=(1, 3)
            )
            
            keywords = {
                'keybert': [
                    {
                        'keyword': kw['keyword'],
                        'score': kw['score'],
                        'rank': idx + 1
                    }
                    for idx, kw in enumerate(keybert_keywords)
                ]
            }
            
            print(f"  Extracted keywords for {paper_id}: {len(keybert_keywords)} keybert")
        except Exception as e:
            print(f"  Warning: Failed to extract keywords for {paper_id}: {e}")
            import traceback
            traceback.print_exc()
        
        existing = collection.find_one({"paper_id": paper_id})
        if existing:
            mongo_doc_id = str(existing['_id'])
            collection.update_one(
                {"paper_id": paper_id},
                {
                    "$set": {
                        "abstract": abstract,
                        "latest_version": version_key,
                        "sections": sections,
                        "chunks": chunks,
                        "summaries": summaries,
                        "keywords": keywords,
                        "metadata": {
                            "total_sections": total_sections,
                            "total_chunks": total_chunks,
                            "word_count": word_count,
                            "keyword_count": len(keywords.get('keybert', []))
                        },
                        "updated_at": datetime.now(UTC).isoformat() + "Z"
                    }
                }
            )
            print(f"  Updated {paper_id} in MongoDB: {mongo_doc_id}")
        else:
            mongo_doc = {
                "paper_id": paper_id,
                "latest_version": version_key,
                "abstract": abstract,
                "sections": sections,
                "chunks": chunks,
                "summaries": summaries,
                "keywords": keywords,
                "metadata": {
                    "total_sections": total_sections,
                    "total_chunks": total_chunks,
                    "word_count": word_count,
                    "keyword_count": len(keywords.get('keybert', []))
                },
                "created_at": datetime.now(UTC).isoformat() + "Z"
            }
            
            try:
                result = collection.insert_one(mongo_doc)
                mongo_doc_id = str(result.inserted_id)
                print(f"  Inserted {paper_id} into MongoDB: {mongo_doc_id}")

                if not update_supabase_mongo_doc_id(supabase_paper_id, mongo_doc_id):
                    collection.delete_one({"_id": result.inserted_id})
                    raise Exception("Failed to update Supabase")
            except Exception as e:
                print(f"  Error inserting {paper_id} into MongoDB: {str(e)}")
                return False
            
        if supabase_paper_id:
            current_mongo_doc_id = paper_data.get('mongo_doc_id')
            if not current_mongo_doc_id or current_mongo_doc_id != mongo_doc_id:
                update_supabase_mongo_doc_id(supabase_paper_id, mongo_doc_id)
                print(f"  Updated Supabase paper_id {supabase_paper_id} with mongo_doc_id: {mongo_doc_id}")
            else:
                print(f"  Supabase already has correct mongo_doc_id")
        
        if supabase_paper_id and keywords:
            try:
                if save_keywords_to_supabase(supabase_paper_id, keywords):
                    print(f"  Saved {len(keywords.get('keybert', []))} keywords to Supabase")
                else:
                    print(f"  Warning: No keywords saved to Supabase")
            except Exception as e:
                print(f"  Warning: Failed to save keywords to Supabase: {e}")
        
        try:
            embedding_service = get_embedding_service()
            
            sections_with_content = reconstruct_sections_with_content(sections, chunks)
            
            full_text = reconstruct_full_text(chunks, abstract)
            
            paper_data_for_embedding = {
                'arxiv_id': arxiv_id,
                'paper_title': paper_data.get('paper_title', ''),
                'abstract': abstract,
                'full_text': full_text,
                'summaries': summaries
            }
            
            if embedding_service.process_paper(paper_data_for_embedding, sections_with_content):
                if supabase_paper_id:
                    update_supabase_embedding_status(supabase_paper_id, "completed")
                embedding_service.save()
                print(f"  Generated and saved embeddings for {paper_id}")
            else:
                if supabase_paper_id:
                    update_supabase_embedding_status(supabase_paper_id, "failed")
                print(f"  Warning: Failed to generate embeddings for {paper_id}")
        except Exception as e:
            print(f"  Error generating embeddings: {e}")
            if supabase_paper_id:
                update_supabase_embedding_status(supabase_paper_id, "failed")
            import traceback
            traceback.print_exc()
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  Error: Invalid JSON in {json_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"  Error processing {json_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # collection.create_index("paper_id", unique=True)
    # collection.create_index("created_at")
    
    # try:
    #     collection.create_index([
    #         ("abstract", "text"),
    #         ("chunks.text", "text"),
    #         ("sections.title", "text")
    #     ], name="text_search_idx")
    #     print("Created text search index")
    # except Exception as e:
    #     print(f"Note: Text index may already exist or failed: {e}")
    
    # try:
    #     collection.create_index("chunks.chunk_id")
    #     collection.create_index("chunks.section_id")
    #     collection.create_index("chunks.section_order")
    #     collection.create_index("chunks.type")
    #     collection.create_index("chunks.order")
    #     print("Created chunk indexes")
    # except Exception as e:
    #     print(f"Note: Chunk indexes may already exist: {e}")
    
    if not ARXIV_PAPERS_DIR.exists():
        print(f"ArXivPapers directory not found: {ARXIV_PAPERS_DIR}")
        return

    processed_ids = set(doc["paper_id"] for doc in collection.find({}, {"paper_id": 1}))
    json_files = []
    for paper_dir in ARXIV_PAPERS_DIR.iterdir():
        if paper_dir.is_dir():
            paper_id = paper_dir.name
            if paper_id not in processed_ids:
                json_file = paper_dir / f"{paper_id}.json"
                if json_file.exists():
                    json_files.append(json_file)
    
    print(f"Found {len(json_files)} paper JSON files")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for json_file in json_files:
        if process_paper_json(json_file):
            success_count += 1
            if success_count >= 300:
                break
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"Import completed!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(json_files)}")

if __name__ == "__main__":
    main()