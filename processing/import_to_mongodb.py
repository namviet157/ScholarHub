from pymongo import MongoClient
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from pathlib import Path
import json
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Tuple
import re

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

# Section patterns to identify sections
SECTION_PATTERNS = [
    (r'\\section\*?\{([^}]*)\}', 'section'),
    (r'\\subsection\*?\{([^}]*)\}', 'subsection'),
    (r'\\subsubsection\*?\{([^}]*)\}', 'subsubsection'),
    (r'\\chapter\*?\{([^}]*)\}', 'chapter'),
]

# Common section titles to map to section_id
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
    """Convert section title to normalized section_id"""
    title_lower = title.lower().strip()
    
    for key, section_id in SECTION_MAPPING.items():
        if key in title_lower:
            return section_id
    
    section_id = re.sub(r'[^a-z0-9]+', '_', title_lower)
    section_id = re.sub(r'_+', '_', section_id).strip('_')
    return section_id[:50]


def extract_section_title(element_content: str) -> Optional[str]:
    """Extract section title from LaTeX command"""
    for pattern, _ in SECTION_PATTERNS:
        match = re.search(pattern, element_content)
        if match:
            return match.group(1)
    return None


def extract_latex_equation(element_content: str) -> Optional[str]:
    """Extract LaTeX equation from element content"""
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
    """Check if element is an equation"""
    return (
        '\\begin{equation' in element_content or
        '\\end{equation' in element_content or
        '$$' in element_content or
        (element_content.count('$') >= 2 and '\\' in element_content)
    )


def infer_node_type(element_content: str) -> str:
    """Infer node type from element content"""
    if '\\document' in element_content.lower():
        return 'DOCUMENT'
    elif '\\abstract' in element_content.lower():
        # Abstract is treated as CHAPTER type (per example format)
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
    """Check if content is meaningful"""
    if not text or len(text.strip()) == 0:
        return False
    
    if node_type in ['EQUATION', 'FORMULA']:
        return len(text) > 3
    
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    if len(words) < 2:
        return False
    
    return len(text) > 15

def parse_hierarchy_to_sections(
    elements: Dict[str, str],
    hierarchy: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Parse hierarchy structure to extract sections with content.
    
    """
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
        section_elem_id = section_info['elem_id']
        section_title = section_info['title']
        
        def collect_content(elem_id: str, visited: set, start_order: int = 1, depth: int = 0) -> Tuple[List[Dict[str, Any]], int]:
            """Recursively collect text content as structured objects, preserving document order.
            Returns (content_list, next_order)"""
            if elem_id in visited or depth > 10:  # Prevent infinite recursion
                return [], start_order
            visited.add(elem_id)
            
            content_list = []
            current_order = start_order
            children = children_map.get(elem_id, [])
            
            for child_id in children:
                child_content = elements.get(child_id, '')
                
                is_subsection = any(re.search(pattern, child_content) for pattern, _ in SECTION_PATTERNS)
                
                if is_subsection:
                    sub_content, next_order = collect_content(child_id, visited, current_order, depth + 1)
                    content_list.extend(sub_content)
                    current_order = next_order
                else:
                    if is_equation(child_content):
                        latex = extract_latex_equation(child_content)
                        if latex:
                            content_list.append({
                                "type": "equation",
                                "latex": latex,
                                "order": current_order
                            })
                            current_order += 1
                    else:
                        if child_content and child_content.strip():
                            content_list.append({
                                "type": "paragraph",
                                "text": child_content,
                                "order": current_order
                            })
                            current_order += 1
            
            return content_list, current_order
        
        content, _ = collect_content(section_elem_id, set())
        
        if content:
            sections.append({
                'section_id': normalize_section_id(section_title),
                'title': section_title,
                'order': idx + 1,
                'content': content
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
        
        full_text_parts = [abstract] if abstract else []
        for section in sections:
            for content_item in section.get('content', []):
                if content_item.get('type') == 'paragraph':
                    full_text_parts.append(content_item.get('text', ''))
                elif content_item.get('type') == 'equation':
                    full_text_parts.append(content_item.get('latex', ''))
        full_text = ' '.join(full_text_parts)
        
        total_sections = len(sections)
        word_count = len(full_text.split()) if full_text else 0
        
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
                        "full_text": full_text,
                        "metadata": {
                            "total_sections": total_sections,
                            "word_count": word_count
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
                "full_text": full_text,
                "metadata": {
                    "total_sections": total_sections,
                    "word_count": word_count
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
    collection.create_index("paper_id", unique=True)
    collection.create_index("created_at")
    if not ARXIV_PAPERS_DIR.exists():
        print(f"ArXivPapers directory not found: {ARXIV_PAPERS_DIR}")
        return
    
    json_files = []
    for paper_dir in ARXIV_PAPERS_DIR.iterdir():
        if paper_dir.is_dir():
            paper_id = paper_dir.name
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
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"Import completed!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(json_files)}")