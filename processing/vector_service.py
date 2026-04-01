import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import re

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIM = 768

EMBEDDINGS_DIR = Path(__file__).parent.parent / "embeddings"
PAPER_INDEX_PATH = EMBEDDINGS_DIR / "paper_index.faiss"
PAPER_METADATA_PATH = EMBEDDINGS_DIR / "paper_metadata.pkl"
SECTION_INDEX_PATH = EMBEDDINGS_DIR / "section_index.faiss"
SECTION_METADATA_PATH = EMBEDDINGS_DIR / "section_metadata.pkl"
CHUNK_INDEX_PATH = EMBEDDINGS_DIR / "chunk_index.faiss"
CHUNK_METADATA_PATH = EMBEDDINGS_DIR / "chunk_metadata.pkl"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


class EmbeddingGenerator:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.array([]).reshape(0, EMBEDDING_DIM)
        
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            return np.array([]).reshape(0, EMBEDDING_DIM)
        
        embeddings = self.model.encode(
            non_empty_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings


class FAISSIndexManager:
    def __init__(self):
        EMBEDDINGS_DIR.mkdir(exist_ok=True)
        
        self.paper_index = None
        self.section_index = None
        self.chunk_index = None
        
        self.paper_metadata = []
        self.section_metadata = []
        self.chunk_metadata = []
        
        self._load_indices()
    
    def _load_indices(self):
        if PAPER_INDEX_PATH.exists() and PAPER_METADATA_PATH.exists():
            try:
                self.paper_index = faiss.read_index(str(PAPER_INDEX_PATH))
                with open(PAPER_METADATA_PATH, 'rb') as f:
                    self.paper_metadata = pickle.load(f)
                print(f"Loaded paper index with {self.paper_index.ntotal} embeddings")
            except Exception as e:
                print(f"Error loading paper index: {e}")
                self._init_paper_index()
        else:
            self._init_paper_index()
        
        if SECTION_INDEX_PATH.exists() and SECTION_METADATA_PATH.exists():
            try:
                self.section_index = faiss.read_index(str(SECTION_INDEX_PATH))
                with open(SECTION_METADATA_PATH, 'rb') as f:
                    self.section_metadata = pickle.load(f)
                print(f"Loaded section index with {self.section_index.ntotal} embeddings")
            except Exception as e:
                print(f"Error loading section index: {e}")
                self._init_section_index()
        else:
            self._init_section_index()
        
        if CHUNK_INDEX_PATH.exists() and CHUNK_METADATA_PATH.exists():
            try:
                self.chunk_index = faiss.read_index(str(CHUNK_INDEX_PATH))
                with open(CHUNK_METADATA_PATH, 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
                print(f"Loaded chunk index with {self.chunk_index.ntotal} embeddings")
            except Exception as e:
                print(f"Error loading chunk index: {e}")
                self._init_chunk_index()
        else:
            self._init_chunk_index()
    
    def _init_paper_index(self):
        self.paper_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.paper_metadata = []
    
    def _init_section_index(self):
        self.section_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.section_metadata = []
    
    def _init_chunk_index(self):
        self.chunk_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.chunk_metadata = []
    
    def add_paper_embeddings(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata must have the same length")
        
        if len(embeddings) == 0:
            return
        
        faiss.normalize_L2(embeddings)
        
        self.paper_index.add(embeddings.astype('float32'))
        self.paper_metadata.extend(metadata)
    
    def add_section_embeddings(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata must have the same length")
        
        if len(embeddings) == 0:
            return
        
        faiss.normalize_L2(embeddings)
        self.section_index.add(embeddings.astype('float32'))
        self.section_metadata.extend(metadata)
    
    def add_chunk_embeddings(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata must have the same length")
        
        if len(embeddings) == 0:
            return
        
        faiss.normalize_L2(embeddings)
        self.chunk_index.add(embeddings.astype('float32'))
        self.chunk_metadata.extend(metadata)
    
    def search_papers(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
        if self.paper_index.ntotal == 0:
            return []
        
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        distances, indices = self.paper_index.search(query_embedding.astype('float32').reshape(1, -1), k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.paper_metadata):
                results.append((float(dist), self.paper_metadata[idx]))
        
        return results
    
    def search_sections(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
        if self.section_index.ntotal == 0:
            return []
        
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        distances, indices = self.section_index.search(query_embedding.astype('float32').reshape(1, -1), k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.section_metadata):
                results.append((float(dist), self.section_metadata[idx]))
        
        return results
    
    def search_chunks(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
        if self.chunk_index.ntotal == 0:
            return []
        
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        distances, indices = self.chunk_index.search(query_embedding.astype('float32').reshape(1, -1), k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.chunk_metadata):
                results.append((float(dist), self.chunk_metadata[idx]))
        
        return results
    
    def save_indices(self):
        faiss.write_index(self.paper_index, str(PAPER_INDEX_PATH))
        with open(PAPER_METADATA_PATH, 'wb') as f:
            pickle.dump(self.paper_metadata, f)
        
        faiss.write_index(self.section_index, str(SECTION_INDEX_PATH))
        with open(SECTION_METADATA_PATH, 'wb') as f:
            pickle.dump(self.section_metadata, f)
        
        faiss.write_index(self.chunk_index, str(CHUNK_INDEX_PATH))
        with open(CHUNK_METADATA_PATH, 'wb') as f:
            pickle.dump(self.chunk_metadata, f)
        
        print(f"Saved indices: {self.paper_index.ntotal} papers, {self.section_index.ntotal} sections, {self.chunk_index.ntotal} chunks")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]: 
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.5:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
    
    return chunks


def clean_text(text: str) -> str:
    if not text:
        return ""
    
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\{|\}', '', text)
    
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


class PaperEmbeddingService:
    def __init__(self):
        self.generator = EmbeddingGenerator()
        self.index_manager = FAISSIndexManager()
    
    def generate_paper_embedding(self, paper_data: Dict[str, Any]) -> Optional[np.ndarray]:
        title = paper_data.get('paper_title', '')
        abstract = paper_data.get('abstract', '')
        full_text = paper_data.get('full_text', '')
        summaries = paper_data.get('summaries', {})
        
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if abstract:
            parts.append(f"Abstract: {abstract}")
        
        document_summary = summaries.get('document_summary') if summaries else None
        abstract_summary = summaries.get('abstract_summary') if summaries else None
        
        if document_summary:
            parts.append(f"Content Summary: {document_summary}")
        elif abstract_summary:
            parts.append(f"Abstract Summary: {abstract_summary}")
        elif full_text:
            summary = full_text[:1000] + "..." if len(full_text) > 1000 else full_text
            parts.append(f"Content: {summary}")
        
        if not parts:
            return None
        
        text = " ".join(parts)
        
        if not text.strip():
            return None
        
        embedding = self.generator.encode([text])[0]
        return embedding
    
    def generate_section_embeddings(self, sections: List[Dict[str, Any]], paper_id: str) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        embeddings_list = []
        metadata_list = []
        
        for section in sections:
            title = section.get('title', '')
            section_id = section.get('section_id', '')
            order = section.get('order', 0)
            
            content_items = section.get('content', [])
            text_parts = [title] if title else []
            
            for item in content_items:
                if item.get('type') == 'paragraph':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'equation':
                    text_parts.append(f"Equation: {item.get('text', '')}")
            
            text = " ".join(text_parts)
            
            if not text.strip():
                continue
            
            embedding = self.generator.encode([text])[0]
            embeddings_list.append(embedding)
            
            metadata_list.append({
                'paper_id': paper_id,
                'section_id': section_id,
                'section_title': title,
                'order': order,
                'text': text[:500]
            })
        
        if not embeddings_list:
            return np.array([]).reshape(0, EMBEDDING_DIM), []
        
        embeddings = np.array(embeddings_list)
        return embeddings, metadata_list
    
    def generate_chunk_embeddings(self, sections: List[Dict[str, Any]], paper_id: str) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        embeddings_list = []
        metadata_list = []
        
        for section in sections:
            section_id = section.get('section_id', '')
            section_title = section.get('title', '')
            order = section.get('order', 0)
            
            text_parts = []
            for item in section.get('content', []):
                if item.get('type') == 'paragraph':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'equation':
                    text_parts.append(item.get('text', ''))
            
            section_text = " ".join(text_parts)
            
            if not section_text.strip():
                continue
            
            chunks = chunk_text(section_text)
            
            for chunk_idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                chunk_with_context = f"{section_title}: {chunk}" if section_title else chunk
                
                embedding = self.generator.encode([chunk_with_context])[0]
                embeddings_list.append(embedding)
                
                metadata_list.append({
                    'paper_id': paper_id,
                    'section_id': section_id,
                    'section_title': section_title,
                    'section_order': order,
                    'chunk_index': chunk_idx,
                    'text': chunk[:300]
                })
        
        if not embeddings_list:
            return np.array([]).reshape(0, EMBEDDING_DIM), []
        
        embeddings = np.array(embeddings_list)
        return embeddings, metadata_list
    
    def process_paper(self, paper_data: Dict[str, Any], sections: List[Dict[str, Any]]) -> bool:
        try:
            paper_id = paper_data.get('arxiv_id') or paper_data.get('paper_id')
            if not paper_id:
                print("  Error: Missing paper_id")
                return False
            
            print(f"  Generating embeddings for {paper_id}...")
            
            paper_embedding = self.generate_paper_embedding(paper_data)
            if paper_embedding is not None:
                self.index_manager.add_paper_embeddings(
                    paper_embedding.reshape(1, -1),
                    [{
                        'paper_id': paper_id,
                        'paper_title': paper_data.get('paper_title', ''),
                        'abstract': paper_data.get('abstract', '')[:500]
                    }]
                )
                print(f"    Added paper-level embedding")
            
            section_embeddings, section_metadata = self.generate_section_embeddings(sections, paper_id)
            if len(section_embeddings) > 0:
                self.index_manager.add_section_embeddings(section_embeddings, section_metadata)
                print(f"    Added {len(section_embeddings)} section-level embeddings")
            
            chunk_embeddings, chunk_metadata = self.generate_chunk_embeddings(sections, paper_id)
            if len(chunk_embeddings) > 0:
                self.index_manager.add_chunk_embeddings(chunk_embeddings, chunk_metadata)
                print(f"    Added {len(chunk_embeddings)} chunk-level embeddings")
            
            return True
            
        except Exception as e:
            print(f"  Error generating embeddings: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search(self, query: str, level: str = "chunk", k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.generator.encode([query])[0]
        
        if level == "paper":
            results = self.index_manager.search_papers(query_embedding, k)
        elif level == "section":
            results = self.index_manager.search_sections(query_embedding, k)
        elif level == "chunk":
            results = self.index_manager.search_chunks(query_embedding, k)
        else:
            raise ValueError(f"Invalid level: {level}. Must be 'paper', 'section', or 'chunk'")
        
        return [
            {
                'score': float(score),
                'metadata': metadata
            }
            for score, metadata in results
        ]
    
    def save(self):
        self.index_manager.save_indices()


_embedding_service = None

def get_embedding_service() -> PaperEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = PaperEmbeddingService()
    return _embedding_service
