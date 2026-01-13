from models import HierarchyNode, NodeType, BibEntry, HIERARCHY_ORDER, LEAF_TYPES
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from collections import defaultdict
from nltk.tokenize import sent_tokenize

class LaTeXFileGatherer:
    # Patterns to match \input and \include commands
    PATTERN = re.compile(r'(?m)^(?![^%\n]*%).*\\(?:input|include)\{([^}]+)\}')
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.included_files: Set[str] = set()
        self.file_contents: Dict[str, str] = {}
        self.file_order: List[str] = []
        
    def gather_files(self, main_file: str) -> Dict[str, str]:
        """
        Recursively gather all files starting from the main file.
        Returns a dict mapping file paths to their contents.
        """
        self.included_files.clear()
        self.file_contents.clear()
        self.file_order.clear()
        
        main_path = self.base_dir / main_file
        self._process_file(main_path)
        
        return self.file_contents
    
    def _resolve_path(self, include_path: str, current_file: Path) -> Path:
        """Resolve the path of an included file"""
        # Add .tex extension if not present
        if not include_path.endswith('.tex'):
            include_path += '.tex'
        
        # Try relative to current file first
        relative_path = current_file.parent / include_path
        if relative_path.exists():
            return relative_path
        
        # Try relative to base directory
        base_relative = self.base_dir / include_path
        if base_relative.exists():
            return base_relative
        
        return relative_path  # Return even if doesn't exist for error reporting
    
    def _process_file(self, file_path: Path) -> str:
        """Process a single file and recursively process includes"""
        # Normalize path for tracking
        normalized_path = str(file_path.resolve())
        
        if normalized_path in self.included_files:
            return ""  # Already processed
        
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            return ""
        
        self.included_files.add(normalized_path)
        self.file_order.append(normalized_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
        
        # Store original content
        self.file_contents[normalized_path] = content
        
        # Find and process all includes
        expanded_content = self._expand_includes(content, file_path)
        
        return expanded_content
    
    def _expand_includes(self, content: str, current_file: Path) -> str:
        """Expand \input and \include commands in content"""
        for match in self.PATTERN.finditer(content):
            include_path = match.group(1)
            resolved_path = self._resolve_path(include_path, current_file)
            self._process_file(resolved_path)
        
        return content
    
    def get_merged_content(self) -> str:
        """Get all content merged into a single string with file markers"""
        merged = []
        for file_path in self.file_order:
            content = self.file_contents.get(file_path, "")
            # Add file marker for tracking
            merged.append(f"%%% FILE: {file_path} %%%\n")
            merged.append(content)
            merged.append("\n")
        return "\n".join(merged)
    
    def get_unused_files(self) -> Set[str]:
        """Get files that exist but are not part of compilation"""
        all_files = set()
        for tex_file in self.base_dir.rglob("*.tex"):
            all_files.add(str(tex_file.resolve()))
        return all_files - self.included_files


class LaTeXCleaner:
    """Cleans and normalizes LaTeX content"""
    
    # Commands to remove (no semantic meaning)
    REMOVE_COMMANDS = [
        r'\\centering',
        r'\\raggedright',
        r'\\raggedleft',
        r'\\noindent',
        r'\\smallskip',
        r'\\medskip',
        r'\\bigskip',
        r'\\newpage',
        r'\\clearpage',
        r'\\pagebreak',
        r'\\linebreak',
        r'\\hfill',
        r'\\vfill',
        r'\\hspace\{[^}]*\}',
        r'\\vspace\{[^}]*\}',
        r'\\phantom\{[^}]*\}',
        r'\\hphantom\{[^}]*\}',
        r'\\vphantom\{[^}]*\}',

        r'\\par',
        r'\\parindent\s*=?\s*[^\\\n]*',
        r'\\parskip\s*=?\s*[^\\\n]*',
        r'\\baselineskip\s*=?\s*[^\\\n]*',
        r'\\stretch\{[^}]*\}',

        # Font / style
        r'\\textbf\{([^}]*)\}',
        r'\\textit\{([^}]*)\}',
        r'\\emph\{([^}]*)\}',
        r'\\underline\{([^}]*)\}',
        r'\\texttt\{([^}]*)\}',
        r'\\bfseries',
        r'\\itshape',
        r'\\ttfamily',
        r'\\footnotesize',
        r'\\scriptsize',
        r'\\tiny',
        r'\\large',
        r'\\Large',
        r'\\LARGE',
        r'\\huge',
        r'\\Huge',
    ]
    
    # Table formatting commands to remove
    TABLE_FORMATTING = [
        r'\\toprule',
        r'\\midrule',
        r'\\bottomrule',
        
        r'\\addlinespace',
        r'\\cmidrule\{[^}]*\}', 
    ]
    
    # Figure/table placement specifiers
    PLACEMENT_SPECS = re.compile(r'\[([htbp!]+)\]')
    
    # Inline math patterns (to normalize to $...$)
    INLINE_MATH_PATTERNS = [
        (re.compile(r'\\[(](.*?)\\[)]', re.DOTALL), r'$\1$'),  # \(...\)
        (re.compile(r'\\begin\{math\}(.*?)\\end\{math\}', re.DOTALL), r'$\1$'),
    ]
    
    # Block math environments (to normalize to equation)
    BLOCK_MATH_ENVS = [
        'displaymath', 'eqnarray', 'eqnarray*', 'align', 'align*',
        'gather', 'gather*', 'multline', 'multline*', 'flalign', 'flalign*'
    ]
    
    def __init__(self):
        # Compile removal patterns
        self.remove_patterns = [re.compile(p) for p in self.REMOVE_COMMANDS + self.TABLE_FORMATTING]
    
    def clean(self, content: str) -> str:
        """Apply all cleaning operations"""
        result = content
        
        # Remove comments (but preserve % in math mode)
        result = self._remove_comments(result)
        result = self.normalize_math(result)
        
        # Remove formatting commands
        for pattern in self.remove_patterns:
            result = pattern.sub('', result)
        
        # Remove placement specifiers
        result = self.PLACEMENT_SPECS.sub('', result)
        
        # Normalize whitespace
        result = self._normalize_whitespace(result)
        
        return result
    
    def normalize_math(self, content: str) -> str:
        """Normalize all math expressions"""
        result = content
        
        # Normalize inline math to $...$
        for pattern, replacement in self.INLINE_MATH_PATTERNS:
            result = pattern.sub(replacement, result)
        
        # Normalize $$...$$ to equation environment
        result = re.sub(
            r'\$\$(.*?)\$\$',
            r'\\begin{equation}\1\\end{equation}',
            result,
            flags=re.DOTALL
        )

        # Normalize \[...\] to equation environment
        result = re.sub(
            r'\\\[(.*?)\\\]',
            r'\\begin{equation}\1\\end{equation}',
            result,
            flags=re.DOTALL
        )
        
        # Normalize other block math environments to equation
        for env in self.BLOCK_MATH_ENVS:
            pattern = re.compile(
                rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}',
                re.DOTALL
            )
            result = pattern.sub(r'\\begin{equation}\1\\end{equation}', result)

        return result
    
    def _remove_comments(self, content: str) -> str:
        """Remove LaTeX comments while preserving escaped %"""
        lines = content.split('\n')
        result_lines = []
        for line in lines:
            # Find % that are not escaped
            new_line = []
            i = 0
            while i < len(line):
                if line[i] == '%' and (i == 0 or line[i-1] != '\\'):
                    break  # Rest of line is comment
                new_line.append(line[i])
                i += 1
            result_lines.append(''.join(new_line))
        return '\n'.join(result_lines)
    
    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace in content"""
        # Replace multiple spaces with single space
        result = re.sub(r'[ \t]+', ' ', content)
        # Replace multiple newlines with double newline
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
    
    def extract_text_content(self, content: str) -> str:
        """Extract plain text from LaTeX, removing commands"""
        result = content
        
        # Remove \command{...} but keep the content in braces
        result = re.sub(r'\\(?:textbf|textit|textrm|texttt|emph|underline)\{([^}]*)\}', r'\1', result)
        
        # Remove \command without braces
        result = re.sub(r'\\(?:bf|it|rm|tt|em|sc)\b', '', result)
        
        # Keep \cite and \ref commands as-is (don't replace with placeholders)
        # Remove labels
        result = re.sub(r'\\label\{[^}]*\}', '', result)
        
        # Remove remaining simple commands EXCEPT \cite, \citep, \citet, \ref, \eqref, \autoref
        result = re.sub(r'\\(?!cite[pt]?\{)(?!ref\{)(?!eqref\{)(?!autoref\{)[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?', '', result)
        
        # Clean up standalone braces (but not those in \cite{} or \ref{})
        # Only remove braces that are not preceded by a backslash command
        result = re.sub(r'(?<!\\cite)(?<!\\citep)(?<!\\citet)(?<!\\ref)(?<!\\eqref)(?<!\\autoref)\{([^{}]*)\}', r'\1', result)
        
        return result.strip()

class HierarchyParser:
    """Parses LaTeX content into a hierarchical structure"""
    
    # Section command patterns with their hierarchy levels
    SECTION_PATTERNS = [
        (r'\\chapter\*?\{([^}]*)\}', NodeType.CHAPTER),
        (r'\\section\*?\{([^}]*)\}', NodeType.SECTION),
        (r'\\subsection\*?\{([^}]*)\}', NodeType.SUBSECTION),
        (r'\\subsubsection\*?\{([^}]*)\}', NodeType.SUBSUBSECTION),
        (r'\\paragraph\*?\{([^}]*)\}', NodeType.PARAGRAPH),
        (r'\\subparagraph\*?\{([^}]*)\}', NodeType.SUBPARAGRAPH),
    ]
    
    # Block math environments
    BLOCK_MATH_ENVS = [
        'equation', 'equation*', 'align', 'align*', 'gather', 'gather*',
        'multline', 'multline*', 'eqnarray', 'eqnarray*', 'displaymath'
    ]
    
    # Figure/table environments
    FLOAT_ENVS = ['figure', 'figure*', 'table', 'table*']
    
    # References section patterns (to exclude)
    REFERENCES_PATTERNS = [
        r'\\begin\{thebibliography\}',
        r'\\bibliography\{',
        r'\\printbibliography',
        r'\\section\*?\{References\}',
        r'\\section\*?\{Bibliography\}',
        r'\\chapter\*?\{References\}',
        r'\\chapter\*?\{Bibliography\}',
    ]
    
    def __init__(self, cleaner: LaTeXCleaner = None):
        self.cleaner = cleaner or LaTeXCleaner()
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.section_patterns = [
            (re.compile(pattern, re.DOTALL), node_type)
            for pattern, node_type in self.SECTION_PATTERNS
        ]
        self.references_pattern = re.compile(
            '|'.join(self.REFERENCES_PATTERNS), re.IGNORECASE
        )
        
        # Block math pattern
        math_env_pattern = '|'.join(re.escape(env) for env in self.BLOCK_MATH_ENVS)
        self.block_math_pattern = re.compile(
            rf'\\begin\{{({math_env_pattern})\}}(.*?)\\end\{{\1\}}|'
            rf'\$\$(.*?)\$\$',
            re.DOTALL
        )
        
        # Figure/table pattern
        float_env_pattern = '|'.join(re.escape(env) for env in self.FLOAT_ENVS)
        self.float_pattern = re.compile(
            rf'\\begin\{{({float_env_pattern})\}}(.*?)\\end\{{\1\}}',
            re.DOTALL
        )
        
        # Label pattern
        self.label_pattern = re.compile(r'\\label\{([^}]*)\}')
        
        # Caption pattern
        self.caption_pattern = re.compile(r'\\caption\{([^}]*)\}')
    
    def _is_references_section(self, content: str) -> bool:
        """Check if content is a references/bibliography section"""
        return bool(self.references_pattern.search(content))
    
    def _get_hierarchy_level(self, node_type: NodeType) -> int:
        """Get the hierarchy level of a node type"""
        try:
            return HIERARCHY_ORDER.index(node_type)
        except ValueError:
            return len(HIERARCHY_ORDER)  # Leaf nodes
    
    def _extract_sections(self, content: str) -> List[Tuple[int, NodeType, str, str]]:
        """
        Extract all section markers from content.
        Returns list of (position, node_type, title, full_match)
        """
        sections = []
        
        # Find all section commands
        for pattern, node_type in self.section_patterns:
            for match in pattern.finditer(content):
                title = match.group(1).strip()
                sections.append((match.start(), node_type, title, match.group(0)))
        
        # Sort by position
        sections.sort(key=lambda x: x[0])
        return sections
    
    def _extract_block_formulas(self, content: str) -> List[Tuple[int, int, str]]:
        """Extract block formulas with their positions"""
        formulas = []
        for match in self.block_math_pattern.finditer(content):
            formula_content = match.group(2) if match.group(2) else match.group(3)
            formulas.append((match.start(), match.end(), formula_content.strip()))
        return formulas
    
    def _extract_floats(self, content: str) -> List[Tuple[int, int, str, str, str]]:
        """Extract figures and tables with their positions"""
        floats = []
        for match in self.float_pattern.finditer(content):
            env_type = match.group(1)
            env_content = match.group(2)
            
            # Extract label
            label_match = self.label_pattern.search(env_content)
            label = label_match.group(1) if label_match else ""
            
            # Extract caption
            caption_match = self.caption_pattern.search(env_content)
            caption = caption_match.group(1) if caption_match else ""
            
            node_type = NodeType.FIGURE if 'figure' in env_type else NodeType.TABLE
            floats.append((match.start(), match.end(), env_content, label, caption, node_type))
        
        return floats
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Clean the text first
        cleaned = self.cleaner.extract_text_content(text)
        
        # Remove \n characters and normalize whitespace
        cleaned = cleaned.replace('\\n', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Protect common patterns that shouldn't be split
        # Store protected patterns with placeholders
        protected_patterns = []
        
        # Protect [No. followed by anything until ] - common in funding/grant numbers
        pattern = r'\[No\.\s*[^\]]*\]'
        matches = list(re.finditer(pattern, cleaned))
        for i, match in enumerate(reversed(matches)):
            placeholder = f"<<<PROTECTED_NO_{len(matches)-i-1}>>>"
            protected_patterns.insert(0, match.group(0))
            cleaned = cleaned[:match.start()] + placeholder + cleaned[match.end():]
        
        # Protect other common abbreviations in brackets
        for abbrev in ['e.g.', 'i.e.', 'et al.', 'vs.', 'cf.']:
            pattern = re.escape(f'[{abbrev}')
            cleaned = cleaned.replace(f'[{abbrev}', f'[{abbrev.replace(".", "<<<DOT>>>")}')
        
        # Use NLTK's sentence tokenizer for better sentence splitting
        sentences = sent_tokenize(cleaned)
        
        # Restore protected patterns
        for i, protected_text in enumerate(protected_patterns):
            placeholder = f"<<<PROTECTED_NO_{i}>>>"
            sentences = [s.replace(placeholder, protected_text) for s in sentences]
        
        # Restore dots in abbreviations
        sentences = [s.replace('<<<DOT>>>', '.') for s in sentences]
        
        # Filter empty sentences and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _create_leaf_nodes(self, content: str, source_file: str = "") -> List[HierarchyNode]:
        """Create leaf nodes (sentences, formulas, figures) from content"""
        nodes = []
        
        # Check if this is a references section
        if self._is_references_section(content):
            return nodes
        
        # Extract formulas and floats first
        formulas = self._extract_block_formulas(content)
        floats = self._extract_floats(content)
        
        # Mark positions of formulas and floats
        excluded_ranges = []
        
        for start, end, formula_content in formulas:
            excluded_ranges.append((start, end))
            nodes.append(HierarchyNode(
                node_type=NodeType.BLOCK_FORMULA,
                content=formula_content,
                source_file=source_file
            ))
        
        for start, end, float_content, label, caption, node_type in floats:
            excluded_ranges.append((start, end))
            nodes.append(HierarchyNode(
                node_type=node_type,
                title=caption,
                content=float_content,
                label=label,
                source_file=source_file
            ))
        
        # Sort excluded ranges
        excluded_ranges.sort()
        
        # Extract text between excluded ranges
        text_segments = []
        last_end = 0
        for start, end in excluded_ranges:
            if start > last_end:
                text_segments.append(content[last_end:start])
            last_end = max(last_end, end)
        if last_end < len(content):
            text_segments.append(content[last_end:])
        
        # Split text into sentences
        full_text = ' '.join(text_segments)
        sentences = self._split_into_sentences(full_text)
        
        for sentence in sentences:
            if sentence and len(sentence) > 10:  # Filter very short fragments
                nodes.append(HierarchyNode(
                    node_type=NodeType.SENTENCE,
                    content=sentence,
                    source_file=source_file
                ))
        
        return nodes
    
    def _extract_abstract(self, content: str, source_file: str):
        pattern = re.compile(
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            re.DOTALL | re.IGNORECASE
        )
        match = pattern.search(content)
        if not match:
            return content, None

        abstract_raw = match.group(1)

        abstract_node = HierarchyNode(
            node_type=NodeType.ABSTRACT,
            title="Abstract",
            source_file=source_file
        )

        abstract_node.children = self._create_leaf_nodes(
            abstract_raw, source_file
        )

        # remove abstract khỏi content chính
        content = content[:match.start()] + content[match.end():]

        return content, abstract_node
    
    def _extract_acknowledgments_content(self, content: str, start: int) -> str:
        """
        Extract acknowledgments content until references/bibliography
        """
        tail = content[start:]

        ref_match = self.references_pattern.search(tail)
        if ref_match:
            return tail[:ref_match.start()]
        return tail


    
    def parse(self, content: str, source_file: str = "") -> HierarchyNode:
        """Parse LaTeX content into a hierarchical tree"""
        # Create root document node
        root = HierarchyNode(
            node_type=NodeType.DOCUMENT,
            title="Document",
            source_file=source_file
        )
        
        # Clean content
        cleaned_content = self.cleaner.clean(content)

        cleaned_content, abstract_node = self._extract_abstract(cleaned_content, source_file)
        if abstract_node:
            root.children.append(abstract_node)
        
        # Extract sections
        sections = self._extract_sections(cleaned_content)
        
        if not sections:
            # No sections found, create leaf nodes directly under root
            root.children = self._create_leaf_nodes(cleaned_content, source_file)
            return root
        
        # Build hierarchy using a stack
        stack = [(root, -1)]  # (node, hierarchy_level)
        
        for i, (pos, node_type, title, full_match) in enumerate(sections):
            # Check if this is a references section
            is_ack = 'acknowledg' in title.lower()

            if self._is_references_section(title) and not is_ack:
                continue

            # Get content until next section
            if i + 1 < len(sections):
                next_pos = sections[i + 1][0]
            else:
                next_pos = len(cleaned_content)
            
            content_start = pos + len(full_match)

            if is_ack:
                section_content = self._extract_acknowledgments_content(
                    cleaned_content, content_start
                )
                node_type = NodeType.ACKNOWLEDGMENTS
            else:
                section_content = cleaned_content[content_start:next_pos]
            
            level = self._get_hierarchy_level(node_type)
            
            # Find parent node
            while stack and stack[-1][1] >= level:
                stack.pop()
            
            parent = stack[-1][0] if stack else root
            
            # Create section node
            section_node = HierarchyNode(
                node_type=node_type,
                title=title,
                source_file=source_file
            )
            
            # Extract label if present at start of section
            label_match = self.label_pattern.search(section_content[:200])
            if label_match:
                section_node.label = label_match.group(1)
            
            # Add leaf nodes (sentences, formulas, figures)
            section_node.children = self._create_leaf_nodes(section_content, source_file)
            
            parent.children.append(section_node)
            stack.append((section_node, level))
        
        return root
    
    def parse_with_file_markers(self, merged_content: str) -> HierarchyNode:
        """Parse merged content that has file markers"""
        # Split by file markers
        file_pattern = re.compile(r'%%% FILE: (.+?) %%%\n')
        parts = file_pattern.split(merged_content)
        
        # Create root
        root = HierarchyNode(
            node_type=NodeType.DOCUMENT,
            title="Document"
        )
        
        # Process each file's content
        current_file = ""
        for i, part in enumerate(parts):
            if i % 2 == 1:  # File path
                current_file = part
            elif part.strip():  # Content
                file_root = self.parse(part, current_file)
                # Merge children into main root
                root.children.extend(file_root.children)
        
        return root

class BibTeXExtractor:
    """Extract and convert bibliography entries from .bbl files and .bib files"""
    
    # Pattern to match \bibitem entries in .bbl files
    BIBITEM_PATTERN = re.compile(
        r'\\bibitem\[([^\]]*)\]\{([^}]+)\}\s*(.*?)(?=\\bibitem|\Z|\\end\{thebibliography\})',
        re.DOTALL
    )
    
    # Alternative pattern without optional argument
    BIBITEM_SIMPLE_PATTERN = re.compile(
        r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem|\Z|\\end\{thebibliography\})',
        re.DOTALL
    )
    
    def __init__(self):
        self.entries: Dict[str, BibEntry] = {}
    
    def _parse_bib_entry(self, content: str, start_pos: int) -> Optional[Tuple[str, str, str, int]]:
        """
        Parse a single BibTeX entry starting from @type{key,...}
        Returns (entry_type, key, fields_content, end_pos) or None
        Handles nested braces correctly.
        """
        # Match @type{key,
        entry_start = re.match(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', content[start_pos:])
        if not entry_start:
            return None
        
        entry_type = entry_start.group(1).lower()
        key = entry_start.group(2).strip()
        
        # Find matching closing brace by counting
        brace_count = 1
        pos = start_pos + entry_start.end()
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        if brace_count != 0:
            return None
        
        # Extract fields content (between key, and final })
        fields_start = start_pos + entry_start.end()
        fields_content = content[fields_start:pos-1]
        
        return (entry_type, key, fields_content, pos)
    
    def _parse_field_value(self, content: str, start_pos: int) -> Tuple[str, int]:
        """
        Parse a field value that can be:
        - {nested {braces} allowed}
        - "quoted string"
        - bare_number
        Returns (value, end_pos)
        """
        pos = start_pos
        
        # Skip whitespace
        while pos < len(content) and content[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= len(content):
            return ("", pos)
        
        # Case 1: Braced value {....}
        if content[pos] == '{':
            brace_count = 1
            value_start = pos + 1
            pos += 1
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            value = content[value_start:pos-1]
            return (value, pos)
        
        # Case 2: Quoted value "..."
        elif content[pos] == '"':
            value_start = pos + 1
            pos += 1
            while pos < len(content) and content[pos] != '"':
                if content[pos] == '\\' and pos + 1 < len(content):
                    pos += 2  # Skip escaped char
                else:
                    pos += 1
            value = content[value_start:pos]
            if pos < len(content):
                pos += 1  # Skip closing quote
            return (value, pos)
        
        # Case 3: Bare value (number or string constant)
        else:
            value_start = pos
            while pos < len(content) and content[pos] not in ',}\n':
                pos += 1
            value = content[value_start:pos].strip()
            return (value, pos)
    
    def _parse_fields(self, fields_content: str) -> Dict[str, str]:
        """
        Parse all fields from the content between @type{key, ... }
        Handles multi-line values and nested braces.
        """
        fields = {}
        pos = 0
        
        while pos < len(fields_content):
            # Skip whitespace and commas
            while pos < len(fields_content) and fields_content[pos] in ' \t\n\r,':
                pos += 1
            
            if pos >= len(fields_content):
                break
            
            # Match field name followed by =
            field_match = re.match(r'(\w+)\s*=\s*', fields_content[pos:])
            if not field_match:
                pos += 1
                continue
            
            field_name = field_match.group(1).lower()
            pos += field_match.end()
            
            # Parse field value
            value, pos = self._parse_field_value(fields_content, pos)
            
            # Handle string concatenation with #
            while pos < len(fields_content):
                # Skip whitespace
                temp_pos = pos
                while temp_pos < len(fields_content) and fields_content[temp_pos] in ' \t\n\r':
                    temp_pos += 1
                
                if temp_pos < len(fields_content) and fields_content[temp_pos] == '#':
                    temp_pos += 1
                    additional_value, temp_pos = self._parse_field_value(fields_content, temp_pos)
                    value += additional_value
                    pos = temp_pos
                else:
                    break
            
            # Clean up the value
            value = re.sub(r'\s+', ' ', value).strip()
            fields[field_name] = value
        
        return fields
        
    def parse_bib_file(self, content: str) -> Dict[str, BibEntry]:
        """Parse a .bib file and extract entries with robust multi-line support"""
        entries = {}
        
        # Find all @type{ patterns
        entry_pattern = re.compile(r'@\w+\s*\{', re.IGNORECASE)
        
        for match in entry_pattern.finditer(content):
            result = self._parse_bib_entry(content, match.start())
            if result:
                entry_type, key, fields_content, end_pos = result
                
                # Skip comments
                if entry_type == 'comment':
                    continue
                
                # Parse fields
                fields = self._parse_fields(fields_content)
                
                if key and (fields or entry_type in ['string', 'preamble']):
                    entries[key] = BibEntry(key=key, entry_type=entry_type, fields=fields)
        
        return entries
    
    def parse_bbl_file(self, content: str) -> Dict[str, BibEntry]:
        """Parse a .bbl file and convert bibitem entries to BibTeX format"""
        entries = {}
        
        # Try pattern with optional citation label
        for match in self.BIBITEM_PATTERN.finditer(content):
            cite_label = match.group(1)
            key = match.group(2).strip()
            entry_content = match.group(3).strip()
            
            entry = self._parse_bibitem_content(key, entry_content)
            if entry:
                entries[key] = entry
        
        # If no entries found, try simple pattern
        if not entries:
            for match in self.BIBITEM_SIMPLE_PATTERN.finditer(content):
                key = match.group(1).strip()
                entry_content = match.group(2).strip()
                
                entry = self._parse_bibitem_content(key, entry_content)
                if entry:
                    entries[key] = entry
        
        return entries
    
    def _parse_bibitem_content(self, key: str, content: str) -> Optional[BibEntry]:
        """
        Parse the content of a bibitem and extract bibliographic fields.
        
        Uses \newblock as anchor points to separate:
        - Author (before first \newblock)
        - Title (second \newblock)
        - Publication info (remaining \newblocks)
        """
        fields = {}
        original_content = content
        
        content = re.sub(r'\s+', ' ', content).strip()
        
        parts = content.split('\\newblock')
        parts = [p.strip() for p in parts if p.strip()]
        
        # If no \newblock found or content is too short, treat as unstructured
        if len(parts) < 2 or len(content) < 50:
            # Save cleaned content as note
            cleaned = self._clean_latex(content)
            if cleaned:
                fields['note'] = cleaned[:500]
            # Try to extract year anyway
            year_match = re.search(r'\b(19|20)\d{2}\b', content)
            if year_match:
                fields['year'] = year_match.group(0)
            return BibEntry(key=key, entry_type='misc', fields=fields)
        
        # Extract Author (first part)
        author_part = parts[0]
        # Remove trailing period if present
        author_part = re.sub(r'\.\s*$', '', author_part)
        # Clean LaTeX formatting commands but keep the text
        author_part = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', author_part)
        author_part = re.sub(r'[{}]', '', author_part)
        if author_part:
            fields['author'] = author_part
        
        # Extract Title (second part)
        if len(parts) >= 2:
            title_part = parts[1]
            # Remove trailing period
            title_part = re.sub(r'\.\s*$', '', title_part)
            # Clean LaTeX but keep text
            title_part = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', title_part)
            title_part = re.sub(r'[{}]', '', title_part).strip()
            if title_part:
                # Wrap in braces to preserve capitalization in BibTeX
                fields['title'] = '{' + title_part + '}'
        
        # Extract Publication Info (remaining parts)
        full_content = content  # Use full content for extraction
        
        # Extract year (4 digits: 19xx or 20xx)
        year_match = re.search(r'\b(19|20)\d{2}\b', full_content)
        if year_match:
            fields['year'] = year_match.group(0)
        
        # Extract journal from \emph{...} or {\em ...}
        journal_match = re.search(r'\\emph\{([^}]+)\}', full_content)
        if not journal_match:
            journal_match = re.search(r'\{\\em\s+([^}]+)\}', full_content)
        if journal_match:
            venue = journal_match.group(1).strip()
            # Determine if journal or conference proceedings
            if any(kw in venue.lower() for kw in ['proc', 'conf', 'workshop', 'symposium', 'international']):
                fields['booktitle'] = venue
            else:
                fields['journal'] = venue
        
        # Extract Volume:Page format (e.g., "87:085115" or "87:1--50")
        vol_page_match = re.search(r'(\d+):(\d+(?:--?\d+)?)', full_content)
        if vol_page_match:
            fields['volume'] = vol_page_match.group(1)
            pages = vol_page_match.group(2).replace('–', '--').replace('-', '--')
            # Normalize single dash to double dash
            if '--' not in pages and re.match(r'\d+\d+', pages):
                pass  # Single page number, keep as is
            fields['pages'] = pages
        else:
            # Try separate volume and pages patterns
            volume_match = re.search(r'vol(?:ume)?\.?\s*(\d+)', full_content, re.IGNORECASE)
            if volume_match:
                fields['volume'] = volume_match.group(1)
            
            pages_match = re.search(r'pages?\s*[:\s]*(\d+(?:\s*[-–]\s*\d+)?)', full_content, re.IGNORECASE)
            if pages_match:
                fields['pages'] = pages_match.group(1).replace('–', '--')
        
        # Extract URL
        url_match = re.search(r'\\url\{([^}]+)\}', full_content)
        if url_match:
            fields['url'] = url_match.group(1)
        
        # Extract DOI
        doi_match = re.search(r'doi[:\s]*([^\s,}]+)', full_content, re.IGNORECASE)
        if doi_match:
            fields['doi'] = doi_match.group(1)
        
        # Determine entry type
        entry_type = self._guess_entry_type(fields, full_content)
        
        # If still missing key fields, add note with original content
        if 'title' not in fields and 'author' not in fields:
            fields['note'] = self._clean_latex(original_content)[:500]
        
        return BibEntry(key=key, entry_type=entry_type, fields=fields)
    
    def _clean_latex(self, content: str) -> str:
        """Remove common LaTeX formatting commands"""
        # Remove \newblock
        content = re.sub(r'\\newblock\s*', '', content)
        # Remove common formatting
        content = re.sub(r'\\textit\{([^}]*)\}', r'\1', content)
        content = re.sub(r'\\textbf\{([^}]*)\}', r'\1', content)
        content = re.sub(r'\\texttt\{([^}]*)\}', r'\1', content)
        content = re.sub(r'\\emph\{([^}]*)\}', r'\1', content)
        # Remove escaped characters
        content = content.replace('\\&', '&')
        content = content.replace('\\~', '~')
        content = content.replace('\\{', '{')
        content = content.replace('\\}', '}')
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    def _guess_entry_type(self, fields: Dict[str, str], content: str) -> str:
        """Guess the BibTeX entry type based on available fields"""
        content_lower = content.lower()
        
        if 'booktitle' in fields or 'proceedings' in content_lower or 'conference' in content_lower:
            return 'inproceedings'
        elif 'journal' in fields:
            return 'article'
        elif 'url' in fields and ('howpublished' in content_lower or 'accessed' in content_lower):
            return 'misc'
        elif 'publisher' in content_lower or 'press' in content_lower:
            return 'book'
        elif 'thesis' in content_lower:
            if 'phd' in content_lower or 'doctoral' in content_lower:
                return 'phdthesis'
            elif 'master' in content_lower:
                return 'mastersthesis'
        elif 'arxiv' in content_lower:
            return 'article'
        
        return 'misc'
    
    def parse_tex_bibitems(self, content: str) -> Dict[str, BibEntry]:
        """
        Parse \bibitem entries directly from .tex file content.
        This handles cases where bibliography is defined inline in the tex file.
        """
        entries = {}
        
        # Look for thebibliography environment
        bib_env_pattern = re.compile(
            r'\\begin\{thebibliography\}.*?(.*?)\\end\{thebibliography\}',
            re.DOTALL
        )
        
        bib_match = bib_env_pattern.search(content)
        if bib_match:
            bib_content = bib_match.group(1)
            
            # Try pattern with optional citation label first
            for match in self.BIBITEM_PATTERN.finditer(bib_content):
                cite_label = match.group(1)
                key = match.group(2).strip()
                entry_content = match.group(3).strip()
                
                entry = self._parse_bibitem_content(key, entry_content)
                if entry:
                    entries[key] = entry
            
            # If no entries found, try simple pattern
            if not entries:
                for match in self.BIBITEM_SIMPLE_PATTERN.finditer(bib_content):
                    key = match.group(1).strip()
                    entry_content = match.group(2).strip()
                    
                    entry = self._parse_bibitem_content(key, entry_content)
                    if entry:
                        entries[key] = entry
        
        return entries
    
    def extract_citation_keys(self, content: str) -> Set[str]:
        """
        Extract all citation keys from \cite, \citep, \citet commands.
        Handles multiple keys in one command: \cite{key1,key2,key3}
        """
        citation_keys = set()
        
        # Pattern to match \cite, \citep, \citet with optional arguments
        # Matches: \cite{key1,key2}, \citep[pre][post]{key1,key2}, etc.
        cite_patterns = [
            re.compile(r'\\cite(?:p|t)?(?:\[[^\]]*\])*(?:\[[^\]]*\])?\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\\citep(?:\[[^\]]*\])*(?:\[[^\]]*\])?\{([^}]+)\}', re.IGNORECASE),
            re.compile(r'\\citet(?:\[[^\]]*\])*(?:\[[^\]]*\])?\{([^}]+)\}', re.IGNORECASE),
        ]
        
        for pattern in cite_patterns:
            for match in pattern.finditer(content):
                keys_str = match.group(1)
                # Split by comma and strip whitespace
                keys = [k.strip() for k in keys_str.split(',') if k.strip()]
                citation_keys.update(keys)
        
        return citation_keys
    
    def load_from_directory(self, base_dir: str, used_citation_keys: Optional[Set[str]] = None) -> Dict[str, BibEntry]:
        """
        Load all bibliography entries from .bib, .bbl, and .tex files in directory.
        If used_citation_keys is provided, only load entries that are actually cited.
        """
        base_path = Path(base_dir)
        
        # Load .bib files (highest priority - already in BibTeX format)
        for bib_file in base_path.rglob('*.bib'):
            try:
                with open(bib_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                entries = self.parse_bib_file(content)
                
                # Filter by used keys if provided
                if used_citation_keys is not None:
                    entries = {k: v for k, v in entries.items() if k in used_citation_keys}
                
                self.entries.update(entries)
                if entries:
                    print(f"    Loaded {len(entries)} entries from {bib_file.name}")
            except Exception as e:
                print(f"Error loading {bib_file}: {e}")
        
        # Load .bbl files
        for bbl_file in base_path.rglob('*.bbl'):
            try:
                with open(bbl_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                entries = self.parse_bbl_file(content)
                
                # Filter by used keys if provided
                if used_citation_keys is not None:
                    entries = {k: v for k, v in entries.items() if k in used_citation_keys}
                
                # Only add entries not already present from .bib files
                new_count = 0
                for key, entry in entries.items():
                    if key not in self.entries:
                        self.entries[key] = entry
                        new_count += 1
                if new_count:
                    print(f"    Loaded {new_count} entries from {bbl_file.name}")
            except Exception as e:
                print(f"Error loading {bbl_file}: {e}")
        
        # Load \bibitem entries from .tex files
        for tex_file in base_path.rglob('*.tex'):
            try:
                with open(tex_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Only parse if file contains thebibliography environment
                if r'\begin{thebibliography}' in content:
                    entries = self.parse_tex_bibitems(content)
                    
                    # Filter by used keys if provided
                    if used_citation_keys is not None:
                        entries = {k: v for k, v in entries.items() if k in used_citation_keys}
                    
                    # Only add entries not already present
                    new_count = 0
                    for key, entry in entries.items():
                        if key not in self.entries:
                            self.entries[key] = entry
                            new_count += 1
                    if new_count:
                        print(f"    Loaded {new_count} bibitem entries from {tex_file.name}")
            except Exception as e:
                print(f"Error loading bibitems from {tex_file}: {e}")
        
        return self.entries

class Deduplicator:
    """Handles deduplication of references and content"""
    
    # Minimum similarity threshold for title fuzzy matching
    TITLE_SIMILARITY_THRESHOLD = 0.6
    
    def __init__(self):
        self.content_hashes: Dict[str, str] = {}  # hash -> unique_id
        self.reference_hashes: Dict[str, str] = {}  # content_hash -> key
        self.key_mappings: Dict[str, str] = {}  # old_key -> canonical_key
        
    # ==================== Reference Deduplication ====================
    
    def _titles_are_similar(self, entry1: BibEntry, entry2: BibEntry) -> bool:
        """
        Check if two entries have similar titles using fuzzy matching.
        Returns True if titles are similar enough to be considered the same reference.
        Returns True if either entry lacks a title (can't verify, allow merge based on other fields).
        """
        title1 = entry1.get_normalized_title()
        title2 = entry2.get_normalized_title()
        
        # If either is empty, we can't compare - allow based on other matching criteria
        if not title1 or not title2:
            return True
        
        # Quick exact match
        if title1 == title2:
            return True
        
        # Compute Jaccard similarity on words
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return True
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0.0
        
        return similarity >= self.TITLE_SIMILARITY_THRESHOLD
    
    def _create_merged_entry(self, canonical: BibEntry, duplicate: BibEntry) -> BibEntry:
        """
        Create a new merged entry without mutating the originals.
        Fields from duplicate are only added if canonical lacks them.
        """
        # Create a copy of canonical's fields
        merged_fields = dict(canonical.fields)
        
        # Add missing fields from duplicate (don't overwrite existing)
        for field, value in duplicate.fields.items():
            if field not in merged_fields or not merged_fields[field].strip():
                if value and value.strip():
                    merged_fields[field] = value
        
        # Return new BibEntry (don't modify original)
        return BibEntry(
            key=canonical.key,
            entry_type=canonical.entry_type,
            fields=merged_fields
        )
    
    def deduplicate_references(self, entries: Dict[str, BibEntry]) -> Dict[str, BibEntry]:
        """
        Deduplicate bibliography entries safely.
        
        - Creates new objects instead of mutating originals
        - Verifies title similarity before merging (fuzzy match)
        - Only merges fields that are missing in canonical entry
        """
        deduplicated: Dict[str, BibEntry] = {}
        hash_to_key: Dict[str, str] = {}
        self.key_mappings.clear()
        
        for key, entry in entries.items():
            content_hash = entry.content_hash()
            
            if content_hash in hash_to_key:
                canonical_key = hash_to_key[content_hash]
                canonical_entry = deduplicated[canonical_key]
                
                # SAFETY CHECK: Verify titles are actually similar
                if not self._titles_are_similar(canonical_entry, entry):
                    # Hash collision but different content - treat as unique
                    # Use a modified hash to differentiate
                    unique_hash = f"{content_hash}_{key}"
                    hash_to_key[unique_hash] = key
                    # Create a copy to avoid mutation
                    deduplicated[key] = BibEntry(
                        key=entry.key,
                        entry_type=entry.entry_type,
                        fields=dict(entry.fields)
                    )
                    self.key_mappings[key] = key
                    continue
                
                # Titles match - safe to merge
                # Create new merged entry (don't mutate canonical)
                merged_entry = self._create_merged_entry(canonical_entry, entry)
                deduplicated[canonical_key] = merged_entry
                
                self.key_mappings[key] = canonical_key
                print(f"Merged duplicate: {key} -> {canonical_key}")
            else:
                # New unique entry - create a copy
                hash_to_key[content_hash] = key
                deduplicated[key] = BibEntry(
                    key=entry.key,
                    entry_type=entry.entry_type,
                    fields=dict(entry.fields)
                )
                self.key_mappings[key] = key

        self.reference_hashes = hash_to_key
        return deduplicated

class LaTeXParser:
    """
    Main LaTeX parser that integrates all components:
    - Multi-file gathering
    - Hierarchy construction
    - Reference extraction
    - Deduplication
    """
    
    ARXIV_ID_PATTERN = re.compile(r'\d{4}-\d{4,5}')
    
    def __init__(self, base_dir: str, paper_id: Optional[str] = None):
        self.base_dir = Path(base_dir)
        self.gatherer = LaTeXFileGatherer(base_dir)
        self.cleaner = LaTeXCleaner()
        self.hierarchy_parser = HierarchyParser(self.cleaner)
        self.bib_extractor = BibTeXExtractor()
        self.deduplicator = Deduplicator()
        
        # Results
        self.hierarchy: Optional[HierarchyNode] = None
        self.references: Dict[str, BibEntry] = {}
        self.file_contents: Dict[str, str] = {}
        self.paper_id = paper_id or self._infer_paper_id()
        
    def _infer_paper_id(self) -> Optional[str]:
        """Best-effort extraction of the arXiv-style paper id from the directory path."""
        search_paths = [self.base_dir] + list(self.base_dir.parents)
        for path in search_paths:
            matches = self.ARXIV_ID_PATTERN.findall(str(path))
            if matches:
                return matches[-1]
        return None

    def _apply_node_ids(self, node: Optional[HierarchyNode]):
        """Prefix all node IDs with the paper id to keep them globally unique."""
        if not node or not self.paper_id:
            return

        prefix = self.paper_id.strip()
        if not prefix:
            return

        def assign(current: HierarchyNode):
            if current.unique_id:
                if not current.unique_id.startswith(f"{prefix}|"):
                    current.unique_id = f"{prefix}|{current.unique_id}"
            else:
                current.unique_id = prefix
            for child in current.children:
                assign(child)

        assign(node)
        
    def parse(self, main_file: str = "main.tex") -> Dict[str, Any]:
        """
        Parse the LaTeX document starting from the main file.
        Returns a dictionary with hierarchy, references, and statistics.
        """
        print(f"Parsing LaTeX document from: {self.base_dir / main_file}")
        print("=" * 60)
        
        # Step 1: Multi-file gathering
        print("\n[1] Gathering files...")
        self.file_contents = self.gatherer.gather_files(main_file)
        print(f"    Found {len(self.file_contents)} files in compilation path")
        
        # Report unused files
        unused = self.gatherer.get_unused_files()
        if unused:
            print(f"    Unused files ({len(unused)}):")
            for f in list(unused)[:5]:
                print(f"      - {Path(f).name}")
            if len(unused) > 5:
                print(f"      ... and {len(unused) - 5} more")
        
        # Step 2: Build hierarchy
        print("\n[2] Building hierarchy...")
        merged_content = self.gatherer.get_merged_content()
        self.hierarchy = self.hierarchy_parser.parse_with_file_markers(merged_content)
        
        hierarchy_stats = self._count_hierarchy_nodes(self.hierarchy)
        print(f"    Built hierarchy with {hierarchy_stats['total']} nodes:")
        for node_type, count in hierarchy_stats['by_type'].items():
            print(f"      - {node_type}: {count}")
        
        # Step 3: Extract citation keys and references
        print("\n[3] Extracting references...")
        # Extract all citation keys from the merged content
        used_citation_keys = self.bib_extractor.extract_citation_keys(merged_content)
        print(f"    Found {len(used_citation_keys)} unique citation keys in document")
        
        # Only load references that are actually cited
        self.references = self.bib_extractor.load_from_directory(str(self.base_dir), used_citation_keys=used_citation_keys)
        print(f"    Loaded {len(self.references)} bibliography entries (only cited references)")
        
        # Finalize IDs with paper prefix
        # self._apply_node_ids(self.hierarchy)
        
        print("\n" + "=" * 60)
        print("Parsing complete!")
        
        return {
            'hierarchy': self.hierarchy,
            'references': self.references,
            'file_contents': self.file_contents,
            'stats': {
                'files': len(self.file_contents),
                'unused_files': len(unused),
                'hierarchy_nodes': hierarchy_stats,
                'references': len(self.references)
            }
        }
    
    def _count_hierarchy_nodes(self, node: HierarchyNode) -> Dict[str, Any]:
        """Count nodes in hierarchy by type"""
        stats = {'total': 0, 'by_type': defaultdict(int)}
        
        def count(n: HierarchyNode):
            stats['total'] += 1
            stats['by_type'][n.node_type.value] += 1
            for child in n.children:
                count(child)
        
        count(node)
        return stats

class MilestoneExporter:
    def __init__(self):
        self.elements: Dict[str, str] = {}  # unique_id -> cleaned content
        self.hierarchy: Dict[str, Dict[str, str]] = {}  # version -> {child_id: parent_id}
        
    def export_document(self, root: HierarchyNode, version: str = "1") -> Dict[str, Any]:
        """
        Export a parsed document to the milestone format.
        
        Args:
            root: The root HierarchyNode of the parsed document
            version: Version identifier (e.g., "1", "2", etc.)
            
        Returns:
            Dictionary in the required format
        """
        self.elements.clear()
        self.hierarchy.clear()
        
        # Process the hierarchy tree
        self._process_node(root, parent_id=None, version=version)
        
        return {
            "elements": self.elements,
            "hierarchy": self.hierarchy
        }
    
    def _process_node(self, node: HierarchyNode, parent_id: Optional[str], version: str):
        """Recursively process nodes to extract elements and build hierarchy"""
        
        # Initialize version hierarchy if not exists
        if version not in self.hierarchy:
            self.hierarchy[version] = {}
        
        current_id = node.unique_id
        
        # For leaf nodes, store the content in elements
        if node.node_type in LEAF_TYPES:
            if node.content:
                # Only store if not already present (deduplication)
                if current_id not in self.elements:
                    self.elements[current_id] = node.content
                
                # Add to hierarchy (child -> parent relationship)
                if parent_id:
                    self.hierarchy[version][current_id] = parent_id
        else:
            # For non-leaf nodes, store section/chapter as full LaTeX command
            if node.title:
                # Map node type to LaTeX command
                type_to_cmd = {
                    NodeType.CHAPTER: "chapter",
                    NodeType.SECTION: "section",
                    NodeType.SUBSECTION: "subsection",
                    NodeType.SUBSUBSECTION: "subsubsection",
                    NodeType.PARAGRAPH: "paragraph",
                    NodeType.SUBPARAGRAPH: "subparagraph",
                    NodeType.ABSTRACT: "abstract",
                    NodeType.ACKNOWLEDGMENTS: "section",
                    NodeType.APPENDIX: "appendix",
                }
                cmd = type_to_cmd.get(node.node_type, node.node_type.value)
                content = f"\\{cmd}{{{node.title}}}"
                if current_id not in self.elements:
                    self.elements[current_id] = content
            
            # Add to hierarchy
            if parent_id:
                self.hierarchy[version][current_id] = parent_id
                
        # Process children
        for child in node.children:
            self._process_node(child, current_id, version)
