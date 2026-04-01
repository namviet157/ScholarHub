import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from processing.data_schemas import BibEntry
import re
import json
from typing import Optional, List, Dict, Any
from processing.latex_engine import LaTeXParser, MilestoneExporter, Deduplicator
from concurrent.futures import ThreadPoolExecutor

MAIN_FILE_CANDIDATES = [
    'main.tex', 'paper.tex', 'article.tex', 'manuscript.tex',
    'thesis.tex', 'document.tex',     'root.tex'
]

# Document class pattern to identify main files
DOCUMENT_CLASS_PATTERN = re.compile(r'\\documentclass', re.IGNORECASE)
BEGIN_DOCUMENT_PATTERN = re.compile(r'\\begin\{document\}', re.IGNORECASE)
AUTHOR_DOCUMENT_PATTERN = re.compile(r'\\author', re.IGNORECASE)

def find_main_file(tex_dir: str) -> Optional[str]:
    """Find the main LaTeX file in a directory."""
    tex_path = Path(tex_dir)
    
    if not tex_path.exists():
        return None
    
    # Strategy 1: Check common names
    for candidate in MAIN_FILE_CANDIDATES:
        candidate_path = tex_path / candidate
        if candidate_path.exists():
            return candidate
    
    # Strategy 2: Find files with documentclass AND begin{document}
    root_tex_files = list(tex_path.glob('*.tex'))
    main_candidates = []
    max_score = -1
    
    for tex_file in root_tex_files:
        try:
            with open(tex_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            has_docclass = DOCUMENT_CLASS_PATTERN.search(content)
            has_begin_doc = BEGIN_DOCUMENT_PATTERN.search(content)
            has_author = AUTHOR_DOCUMENT_PATTERN.search(content)
            
            score = 0
            if has_docclass: score += 2
            if has_begin_doc: score += 2
            if has_author: score += 1
            if r'\section' in content: score += 1
            
            if score > max_score:
                max_score = score
                main_candidates = [tex_file.name]
            elif score == max_score:
                main_candidates.append(tex_file.name)    
        except Exception:
            continue
    
    if len(main_candidates) == 1:
        return main_candidates[0]
    elif len(main_candidates) > 1:
        # Prefer shorter filenames (less likely to be appendix, etc.)
        return min(main_candidates, key=len)
    
    # Strategy 3: If only one tex file at root level
    if len(root_tex_files) == 1:
        return root_tex_files[0].name
    
    # Strategy 4: Look for any tex file with documentclass
    for tex_file in root_tex_files:
        try:
            with open(tex_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if DOCUMENT_CLASS_PATTERN.search(content):
                return tex_file.name
        except Exception:
            continue
    
    return None

class MultiVersionProcessor:
    """Process multiple versions of the same paper."""
    
    def __init__(self, paper_dir: str):
        self.paper_dir = Path(paper_dir)
        self.arxiv_id = self.paper_dir.name
        
        tex_dir_candidate = self.paper_dir / 'tex'
        self.tex_dir = tex_dir_candidate if tex_dir_candidate.exists() else self.paper_dir
        
        self.versions: Dict[str, Path] = {}
        self.results: Dict[str, Any] = {}
        
    def discover_versions(self) -> List[str]:
        """Find all version directories (e.g., 2305-14596v1, 2305-14596v2)."""
        self.versions.clear()
        
        if not self.tex_dir.exists():
            return []
        
        # Look for version folders
        version_pattern = re.compile(rf'{re.escape(self.arxiv_id)}v(\d+)', re.IGNORECASE)
        
        for item in self.tex_dir.iterdir():
            if item.is_dir():
                match = version_pattern.match(item.name)
                if match:
                    version_num = match.group(1)
                    self.versions[version_num] = item
        
        # Sort versions numerically
        return sorted(self.versions.keys(), key=int)
    
    def parse_version(self, version: str) -> Optional[Dict[str, Any]]:
        """Parse a specific version of the paper."""
        if version not in self.versions:
            return None
        
        version_dir = self.versions[version]
        main_file = find_main_file(str(version_dir))
        
        if not main_file:
            print(f"  Warning: Could not find main file in {version_dir}")
            return None
        
        try:
            parser = LaTeXParser(str(version_dir))
            result = parser.parse(main_file)
            return {
                'parser': parser,
                'result': result,
                'main_file': main_file
            }
        except Exception as e:
            print(f"  Error parsing version {version}: {e}")
            return None
    
    def process_all_versions(self) -> Dict[str, Any]:
        """Process all versions and return combined results."""
        versions = self.discover_versions()
        
        if not versions:
            print(f"  No versions found for {self.arxiv_id}")
            return {}
        
        print(f"  Found {len(versions)} version(s): {versions}")
        
        for version in versions:
            print(f"\n  Processing version {version}...")
            result = self.parse_version(version)
            if result:
                self.results[version] = result
        
        return self.results
    
    def export_combined(self) -> Optional[Path]:
        """
        Export combined results for all versions.
        Elements are deduplicated across versions.
        Each version has its own hierarchy.
        References are deduplicated and merged across versions.
        Files are saved directly to the paper directory.
        """
        if not self.results:
            return None
        
        exporter = MilestoneExporter()
        combined_elements = {}
        combined_hierarchy = {}
        
        # Collect all references from all versions for cross-version deduplication
        all_references: Dict[str, BibEntry] = {}
        for version, data in self.results.items():
            parser = data['parser']
            for key, entry in parser.references.items():
                if key not in all_references:
                    # Create a copy of the entry
                    all_references[key] = BibEntry(
                        key=entry.key,
                        entry_type=entry.entry_type,
                        fields=dict(entry.fields)
                    )
                else:
                    # Merge fields from this version's entry (unionize)
                    existing = all_references[key]
                    for field, value in entry.fields.items():
                        if field not in existing.fields or not existing.fields[field].strip():
                            if value and value.strip():
                                existing.fields[field] = value
        
        # Deduplicate references across all versions
        # This handles entries with DIFFERENT keys but SAME content
        deduplicator = Deduplicator()
        original_count = len(all_references)
        deduplicated_refs = deduplicator.deduplicate_references(all_references)
        
        if original_count > len(deduplicated_refs):
            print(f"  Cross-version reference deduplication: {original_count} -> {len(deduplicated_refs)} entries")
        
        print(f"  Exporting {len(deduplicated_refs)} unique cited references to .bib file")
        
        for version, data in self.results.items():
            parser = data['parser']
            if parser.hierarchy:
                # Export this version
                version_data = exporter.export_document(parser.hierarchy, version=version)
                
                # Merge elements (deduplicated by ID)
                combined_elements.update(version_data['elements'])
                
                # Add version hierarchy
                combined_hierarchy.update(version_data['hierarchy'])
        
        # Create output structure
        output_data = {
            'elements': combined_elements,
            'hierarchy': combined_hierarchy
        }
        
        # Save files directly to paper directory
        # Save main JSON file
        main_json = self.paper_dir / f"{self.arxiv_id}.json"
        with open(main_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Export deduplicated BibTeX references (already merged across versions)
        all_bibtex = {}
        for key, entry in deduplicated_refs.items():
            all_bibtex[key] = BibEntry(
                key=key,
                entry_type=entry.entry_type,
                fields=entry.fields
            )
        
        if all_bibtex:
            bibtex_file = self.paper_dir / f"{self.arxiv_id}_bibtex.bib"
            
            with open(bibtex_file, 'w', encoding='utf-8') as f:
                for entry in all_bibtex.values():
                    f.write(entry.to_bibtex() + "\n\n")
        
        return self.paper_dir

class BatchProcessor:
    def __init__(self, folder: str, sync_to_backend: bool = False):
        self.folder = Path(folder)
        self.sync_to_backend = sync_to_backend
        
        self.papers: List[Path] = []
        self.results: Dict[str, Any] = {}
        self.stats = {
            'total_papers': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_elements': 0,
            'total_versions': 0
        }
    
    def discover_papers(self) -> List[str]:
        self.papers.clear()
        
        arxiv_pattern = re.compile(r'\d{4}-\d{4,5}')

        for item in sorted(self.folder.iterdir()):
            if item.is_dir() and arxiv_pattern.match(item.name):
                files = [file.name for file in item.iterdir()]
                if f'{item.name}.json' not in files or f'{item.name}_bibtex.bib' not in files:
                    self.papers.append(item)
        
        self.stats['total_papers'] = len(self.papers)
        return [p.name for p in self.papers]
    
    def process_paper(self, paper_dir: Path) -> Optional[Dict[str, Any]]:
        """Process a single paper with all its versions."""
        processor = MultiVersionProcessor(str(paper_dir))
        results = processor.process_all_versions()
        
        if results:
            output_path = processor.export_combined()
            if self.sync_to_backend and output_path:
                from processing import db_orchestrator
                json_file = output_path / f"{paper_dir.name}.json"
                if json_file.exists():
                    db_orchestrator.process_paper_json(json_file)
            
            # Calculate stats
            total_elements = 0
            for version_data in results.values():
                parser = version_data.get('parser')
                if parser and parser.hierarchy:
                    def count_nodes(node):
                        count = 1
                        for child in node.children:
                            count += count_nodes(child)
                        return count
                    total_elements += count_nodes(parser.hierarchy)
            
            return {
                'arxiv_id': paper_dir.name,
                'versions_processed': len(results),
                'output_path': output_path,
                'total_elements': total_elements,
                'has_tex': True
            }
        else:
            # Paper has no tex files
            return {
                'arxiv_id': paper_dir.name,
                'versions_processed': 0,
                'output_path': paper_dir,
                'total_elements': 0,
                'has_tex': False
            }
    
    def process_all(self, limit: int = None, verbose: bool = True, max_workers: int = 5) -> Dict[str, Any]:
        """
        Process all papers in the folder using ThreadPoolExecutor for parallel processing.
        
        Args:
            limit: Maximum number of papers to process (for testing)
            verbose: Whether to print progress
            max_workers: Maximum number of worker threads
        """
        papers = self.discover_papers()
        
        if not papers:
            print(f"No papers found in {self.folder}")
            return self.stats
        
        print(f"{'='*60}")
        print(f"Found {len(papers)} papers to process")
        print(f"{'='*60}\n")
        
        papers_to_process = self.papers[:limit] if limit else self.papers
        
        def process_single_paper(args):
            """Wrapper function to process a single paper with index tracking."""
            idx, paper_dir = args
            arxiv_id = paper_dir.name
            
            if verbose:
                print(f"\n[{idx}/{len(papers_to_process)}] Processing {arxiv_id}...")
                print("-" * 40)
            
            try:
                result = self.process_paper(paper_dir)
                
                if result:
                    if result.get('has_tex', True):
                        if verbose:
                            print(f"  Successfully processed {result['versions_processed']} version(s)")
                            print(f"  Elements: {result['total_elements']}")
                    else:
                        if verbose:
                            print(f"  Folder created with metadata/references (no .tex files)")
                    return (idx, arxiv_id, result, None)
                else:
                    if verbose:
                        print(f"  Skipped (no versions found or parse failed)")
                    return (idx, arxiv_id, None, 'skipped')
            except Exception as e:
                if verbose:
                    print(f"  Failed: {str(e)}")
                return (idx, arxiv_id, None, str(e))
        
        # Process papers in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_single_paper, enumerate(papers_to_process, 1)))
        
        # Sort results by index to maintain order
        results.sort(key=lambda x: x[0])
        
        # Process results and update stats
        for idx, arxiv_id, result, error in results:
            if error == 'skipped':
                self.stats['skipped'] += 1
            elif error:
                self.stats['failed'] += 1
            elif result:
                self.results[arxiv_id] = result
                self.stats['processed'] += 1
                
                if result.get('has_tex', True):
                    self.stats['total_versions'] += result['versions_processed']
                    self.stats['total_elements'] += result['total_elements']
        
        # Save processing summary
        summary_file = self.folder / 'processing_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': self.stats,
                'papers': {
                    arxiv_id: {
                        'versions_processed': r['versions_processed'],
                        'total_elements': r['total_elements']
                    }
                    for arxiv_id, r in self.results.items()
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Summary saved to: {summary_file}")
        
        return self.stats

if __name__ == "__main__":
    FOLDER = str(_REPO_ROOT / "ArXivPapers")
    batch_processor = BatchProcessor(FOLDER, sync_to_backend=False)

    papers = batch_processor.discover_papers()
    print(f"Found {len(papers)} papers in {FOLDER}")

    stats = batch_processor.process_all(limit=None, verbose=True)