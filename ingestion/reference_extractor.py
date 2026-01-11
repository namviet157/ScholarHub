import requests
import json
import os
import time
import re
from dotenv import load_dotenv

load_dotenv()

def format_arxiv_id_for_key(arxiv_id):
    """
    Convert arXiv ID to folder format (yymm-nnnnn).
    Examples:
        "2305.04793" -> "2305-04793"
        "2305.04793v1" -> "2305-04793"
    """
    # Remove version suffix if present
    clean_id = re.sub(r'v\d+$', '', arxiv_id)
    # Replace dot with dash
    return clean_id.replace('.', '-')


def get_paper_references(arxiv_id, delay=3, max_retries=5):
    """Fetch references from Semantic Scholar API with retries."""
    clean_id = re.sub(r'v\d+$', '', arxiv_id)
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{clean_id}"
    params = {
        "fields": "references,references.title,references.authors,references.year,references.venue,references.externalIds,references.publicationDate"
    }

    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                references = data.get("references", [])
                return references, len(references) if references else 0
            elif response.status_code == 404:
                return None, 0
            elif response.status_code == 429:
                time.sleep(delay)
                retries += 1
            else:
                time.sleep(delay)
                retries += 1
        except requests.exceptions.RequestException:
            time.sleep(delay)
            retries += 1

    return None, 0


def convert_to_references_dict(references):
    """Convert Semantic Scholar references to dict format."""
    result = {}

    for ref in references:
        if not ref:
            continue

        external_ids = ref.get("externalIds", {}) or {}
        arxiv_id = external_ids.get("ArXiv", "")

        if not arxiv_id:
            continue

        key = format_arxiv_id_for_key(arxiv_id)
        authors_list = ref.get("authors", [])
        authors = [author.get("name", "") for author in authors_list if author.get("name")]

        publication_date = ref.get("publicationDate", "")
        year = ref.get("year")
        if not publication_date and year:
            publication_date = f"{year}-01-01"

        metadata = {
            "paper_title": ref.get("title", ""),
            "authors": authors,
            "submission_date": publication_date if publication_date else "",
            "semantic_scholar_id": ref.get("paperId")
        }

        result[key] = metadata

    return result


def extract_references_for_paper(arxiv_id, save_dir="./ArXivPapers"):
    """Extract references for a paper and save to references.json."""
    paper_id_key = format_arxiv_id_for_key(arxiv_id)
    paper_folder = os.path.join(save_dir, paper_id_key)

    if not os.path.exists(paper_folder):
        return False

    try:
        json_path = os.path.join(paper_folder, "references.json")
        references, total_found = get_paper_references(arxiv_id)

        if references is None or total_found == 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return False

        references_dict = convert_to_references_dict(references)
        if not references_dict:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return False

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(references_dict, f, indent=4, ensure_ascii=False)

        return True

    except Exception:
        return False
