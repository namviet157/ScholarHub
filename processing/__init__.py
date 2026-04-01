"""
Paper pipeline: LaTeX → structured JSON, optional MongoDB / Supabase / FAISS.
"""

from .batch_manager import (
    BatchProcessor,
    MultiVersionProcessor,
    find_main_file,
    MAIN_FILE_CANDIDATES,
)
from .data_schemas import (
    BibEntry,
    HierarchyNode,
    NodeType,
    HIERARCHY_ORDER,
    LEAF_TYPES,
)
from .ai_summarizer import get_summarizer
from .ai_keyword_extractor import get_keyword_extractor

from .db_orchestrator import process_all_papers
__all__ = [
    "BatchProcessor",
    "MultiVersionProcessor",
    "find_main_file",
    "MAIN_FILE_CANDIDATES",
    "BibEntry",
    "HierarchyNode",
    "NodeType",
    "HIERARCHY_ORDER",
    "LEAF_TYPES",
    "get_summarizer",
    "get_keyword_extractor",
    "process_all_papers",
]
