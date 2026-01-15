import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class NodeType(Enum):
    """Types of nodes in the document hierarchy"""
    DOCUMENT = "document"
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"
    SUBSUBSECTION = "subsubsection"
    PARAGRAPH = "paragraph"
    SUBPARAGRAPH = "subparagraph"
    # Leaf nodes
    SENTENCE = "sentence"
    BLOCK_FORMULA = "block_formula"
    FIGURE = "figure"
    TABLE = "table"
    # Special
    ABSTRACT = "abstract"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"


# Hierarchy order for determining nesting levels
HIERARCHY_ORDER = [
    NodeType.DOCUMENT,
    NodeType.CHAPTER,
    NodeType.SECTION,
    NodeType.SUBSECTION,
    NodeType.SUBSUBSECTION,
    NodeType.PARAGRAPH,
    NodeType.SUBPARAGRAPH,
]

# Leaf node types (smallest elements)
LEAF_TYPES = {NodeType.SENTENCE, NodeType.BLOCK_FORMULA, NodeType.FIGURE, NodeType.TABLE}

NODE_ID_LENGTH = 12

@dataclass
class HierarchyNode:
    """A node in the document hierarchy tree"""
    node_type: NodeType
    title: str = ""
    content: str = ""
    children: List['HierarchyNode'] = field(default_factory=list)
    label: str = ""
    source_file: str = ""
    content_hash: str = ""
    unique_id: str = ""
    
    def __post_init__(self):
        # Generate content hash first (used for deduplication)
        if not self.content_hash and self.content:
            # Normalize content for consistent hashing
            normalized_content = re.sub(r'\s+', ' ', self.content.strip().lower())
            self.content_hash = hashlib.md5(normalized_content.encode()).hexdigest()
        
        # Generate unique_id
        if not self.unique_id:
            # For leaf nodes (sentences, formulas, figures, tables), use content-based ID
            # This ensures identical content across versions gets the same ID
            if self.node_type in LEAF_TYPES and self.content_hash:
                self.unique_id = self.content_hash[:NODE_ID_LENGTH]
            else:
                # For structural nodes, use type + title + content prefix
                self.unique_id = hashlib.md5(
                    f"{self.node_type.value}:{self.title}:{self.content[:100]}".encode()
                ).hexdigest()[:NODE_ID_LENGTH]

@dataclass 
class BibEntry:
    """A bibliography entry"""
    key: str
    entry_type: str
    fields: Dict[str, str] = field(default_factory=dict)
    
    def _normalize_field(self, value: str) -> str:
        """Normalize a field value for comparison"""
        if not value:
            return ""
        normalized = value.lower().strip()
        normalized = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', normalized)
        normalized = re.sub(r'[{}"\'.,;:\-]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def get_normalized_title(self) -> str:
        """Get normalized title for fuzzy comparison"""
        return self._normalize_field(self.fields.get('title', ''))
    
    def get_normalized_author(self) -> str:
        """Get normalized author for fuzzy comparison"""
        return self._normalize_field(self.fields.get('author', ''))
    
    def has_sufficient_fields(self) -> bool:
        """Check if entry has enough fields for content-based deduplication"""
        title = self.fields.get('title', '').strip()
        author = self.fields.get('author', '').strip()
        year = self.fields.get('year', '').strip()
        doi = self.fields.get('doi', '').strip()
        
        # Need at least title or (author + year) or doi
        has_title = len(title) > 5
        has_author_year = len(author) > 3 and len(year) >= 4
        has_doi = len(doi) > 5
        
        return has_title or has_author_year or has_doi
    
    def content_hash(self) -> str:
        """
        Generate hash based on content for deduplication
        Returns unique key-based hash if fields are insufficient
        """
        # If fields are empty or insufficient, return key-based hash to prevent false merges
        if not self.fields or not self.has_sufficient_fields():
            unique_str = f"__KEY_ONLY__:{self.key}:{self.entry_type}"
            return hashlib.md5(unique_str.encode()).hexdigest()
        
        # Build hash
        hash_parts = []
        
        # Title (primary identifier)
        title = self.get_normalized_title()
        if title:
            hash_parts.append(f"title:{title}")
        
        # Author (secondary identifier)  
        author = self.get_normalized_author()
        if author:
            # Extract first author's last name
            first_author = author.split(' and ')[0].strip()
            hash_parts.append(f"author:{first_author}")
        
        # Year
        year = self.fields.get('year', '').strip()
        if year:
            hash_parts.append(f"year:{year}")
        
        # DOI (very reliable identifier if present)
        doi = self._normalize_field(self.fields.get('doi', ''))
        if doi:
            hash_parts.append(f"doi:{doi}")
        
        if not hash_parts:
            # Fallback to key-based hash
            unique_str = f"__KEY_ONLY__:{self.key}:{self.entry_type}"
            return hashlib.md5(unique_str.encode()).hexdigest()
        
        content = "|".join(sorted(hash_parts))
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_bibtex(self, indent: int = 4) -> str:
        indent_str = " " * indent
        lines = [f"@{self.entry_type}{{{self.key},"]
        for key, value in self.fields.items():
            lines.append(f"{indent_str}{key} = {{{value}}},")
        lines.append("}")
        return "\n".join(lines)
    