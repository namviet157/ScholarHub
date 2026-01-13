import arxiv
import os
import re
import json
import time
import tarfile
import shutil
import subprocess
import gzip
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

SAVE_DIR = "./ArXivPapers"


def detect_and_fix_filetype(tar_path):
    """Detect file type using 'file' command or fallback to extension."""
    try:
        result = subprocess.run(["file", tar_path], capture_output=True, text=True, errors='ignore')
        output = result.stdout.strip()
    except FileNotFoundError:
        # Fallback: check extension
        if tar_path.endswith('.tar.gz') or tar_path.endswith('.tgz'):
            return "tar.gz", None
        elif tar_path.endswith('.gz'):
            return "gz", None
        return "unknown", None
    except Exception:
        return "unknown", None

    if "PDF document" in output:
        return "pdf", None
    elif "gzip compressed data" in output:
        match = re.search(r', was "([^"]+)"', output)
        if match:
            return "gz", os.path.basename(match.group(1))
        else:
            return "tar.gz", None
    elif "tar archive" in output:
        return "tar.gz", None
    else:
        return "unknown", None


def extract_and_clean(tar_path, dest_folder, base_name):
    """Extract and clean archive, keeping only .tex and .bib files."""
    filetype, orig_name = detect_and_fix_filetype(tar_path)
    extract_path = os.path.join(dest_folder, base_name)
    os.makedirs(extract_path, exist_ok=True)

    if filetype == "pdf":
        return (True, 0)
    if filetype == "unknown":
        return (False, 0)

    try:
        if filetype == "tar.gz":
            with tarfile.open(tar_path, 'r:*') as tar:
                tar.extractall(path=extract_path)
        elif filetype == "gz":
            out_name = orig_name or f"{base_name}.file"
            out_path = os.path.join(extract_path, out_name)
            with gzip.open(tar_path, 'rb') as fin, open(out_path, 'wb') as fout:
                shutil.copyfileobj(fin, fout)
    except Exception:
        shutil.rmtree(extract_path, ignore_errors=True)
        return (False, 0)

    deleted = 0
    for root, _, files in os.walk(extract_path):
        for f in files:
            if not f.lower().endswith(('.tex', '.bib')):
                try:
                    os.remove(os.path.join(root, f))
                    deleted += 1
                except:
                    pass
    return (True, deleted)


def crawl_single_paper(arxiv_id, save_dir=SAVE_DIR):
    """Download and process a single arXiv paper with all its versions."""
    if '.' not in arxiv_id:
        return False

    client = arxiv.Client()
    prefix, suffix = arxiv_id.split('.')
    paper_folder = os.path.join(save_dir, f"{prefix}-{suffix}")
    tex_folder = os.path.join(paper_folder, "tex")
    os.makedirs(tex_folder, exist_ok=True)

    try:
        search = arxiv.Search(id_list=[arxiv_id])
        base_paper = next(client.results(search))
        match = re.search(r'v(\d+)$', base_paper.entry_id)
        latest_version = int(match.group(1)) if match else 1
    except (StopIteration, Exception):
        return False

    title = base_paper.title
    authors = [a.name for a in base_paper.authors]
    abstract = base_paper.summary
    submission_date = base_paper.published.strftime("%Y-%m-%d") if base_paper.published else None
    publication_venue = base_paper.journal_ref if base_paper.journal_ref else None
    categories = base_paper.categories
    revised_dates = []

    if latest_version > 1:
        for v in range(2, latest_version + 1):
            try:
                vid = f"{arxiv_id}v{v}"
                search_v = arxiv.Search(id_list=[vid])
                paper_v = next(client.results(search_v))
                revised_dates.append(paper_v.updated.strftime("%Y-%m-%d") if paper_v.updated else None)
            except:
                revised_dates.append(None)

    pdf_url = base_paper.pdf_url if base_paper.pdf_url else None

    metadata = {
        "arxiv_id": arxiv_id.replace('.', '-'),
        "paper_title": title,
        "abstract": abstract,
        "authors": authors,
        "submission_date": submission_date,
        "revised_dates": revised_dates,
        "publication_venue": publication_venue,
        "latest_version": latest_version,
        "categories": categories,
        "pdf_url": pdf_url
    }

    metadata_path = os.path.join(paper_folder, "metadata.json")
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
    except Exception:
        return False

    versions_processed = 0
    for v in range(1, latest_version + 1):
        version_id = f"{arxiv_id}v{v}"
        version_folder_name = f"{prefix}-{suffix}v{v}"
        temp_tar = os.path.join(paper_folder, f"{version_id}.tar.gz")

        try:
            search_v = arxiv.Search(id_list=[version_id])
            paper_v = next(client.results(search_v))
            paper_v.download_source(dirpath=paper_folder, filename=f"{version_id}.tar.gz")

            success, _ = extract_and_clean(temp_tar, tex_folder, version_folder_name)
            if success:
                versions_processed += 1

            try:
                os.remove(temp_tar)
            except:
                pass

            time.sleep(0.3)

        except (StopIteration, Exception):
            continue

    return versions_processed > 0
