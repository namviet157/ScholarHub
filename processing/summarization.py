import torch
from transformers import PegasusTokenizer, PegasusForConditionalGeneration
from typing import Dict, List, Optional, Any
import re


class PaperSummarizer:
    
    def __init__(self, model_name: str = "google/pegasus-arxiv"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        
        print(f"Loading summarization model: {model_name}")
        try:
            self.tokenizer = PegasusTokenizer.from_pretrained(model_name)
            self.model = PegasusForConditionalGeneration.from_pretrained(model_name).to(self.device)
            self.model.eval()
            print(f"Summarization model loaded successfully on {self.device}")
        except Exception as e:
            print(f"Error loading summarization model: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = re.sub(r'<n>', ' ', text)  # Replace <n> with space
        text = re.sub(r'<[^>]+>', '', text)  # Remove other XML/HTML-like tags
        
        text = re.sub(r'@x[a-z]+', '', text)  # @xcite, @xref, etc.
        text = re.sub(r'@cite\{[^}]*\}', '', text)
        text = re.sub(r'\[@cite[^\]]*\]', '', text)
        text = re.sub(r'\\cite\{[^}]*\}', '', text)
        text = re.sub(r'\\ref\{[^}]*\}', '', text)
        
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        text = re.sub(r'\{|\}', '', text)
        
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        text = re.sub(r'\+\s*<n>|\+\s+', ' ', text)  # Remove + symbols
        text = re.sub(r'[\[\]]', '', text)  # Remove square brackets
        
        text = re.sub(r'\d{2}[A-Z]\d{2}', '', text)  # e.g., 65N15
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Fix spacing before punctuation
        text = re.sub(r'([.,;:!?])\1+', r'\1', text)  # Remove duplicate punctuation
        text = text.strip()
        
        return text
    
    def post_process_summary(self, summary: str) -> str:
        if not summary:
            return ""
        
        summary = re.sub(r'<n>', ' ', summary)
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = re.sub(r'@x[a-z]+', '', summary)
        
        summary = re.sub(r'\*\*?', '', summary)
        summary = re.sub(r'__?', '', summary)
        summary = re.sub(r'\+\s*', '', summary)
        
        summary = re.sub(r'([.,;:!?])\1+', r'\1', summary)
        summary = re.sub(r'\s+([.,;:!?])', r'\1', summary)
        
        summary = re.sub(r'\s+', ' ', summary)
        summary = summary.strip()
        
        if summary and summary[0].islower():
            summary = summary[0].upper() + summary[1:]
        
        if summary and summary[-1] not in '.!?':
            summary += '.'
        
        return summary
    
    def split_text_into_chunks(self, text: str, max_length: int = 1024) -> List[str]:
        if len(text) <= max_length:
            return [text]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def summarize_abstract(self, abstract: str, max_length: int = 150, min_length: int = 30) -> Optional[str]:
        if not abstract or len(abstract.strip()) < 50:
            return None
        
        abstract = self.clean_text(abstract)
        
        try:
            inputs = self.tokenizer(
                abstract,
                max_length=512,
                truncation=True,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_length=max_length,
                    min_length=min_length,
                    num_beams=2,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    length_penalty=2.0
                )
            
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summary = self.post_process_summary(summary)
            return summary if summary else None
            
        except Exception as e:
            print(f"Error summarizing abstract: {e}")
            return None
    
    def summarize_long_document(
        self,
        text: str,
        max_length: int = 1024,
        min_length: int = 256,
        chunk_max_length: int = 1024,
        batch_size: int = 4
    ) -> Optional[str]:
        if not text or len(text.strip()) < 200:
            return None
        
        text = self.clean_text(text)
        
        if len(text) <= chunk_max_length:
            return self._summarize_single_text(text, max_length, min_length)
        

        chunks = self.split_text_into_chunks(text, chunk_max_length)
        
        if not chunks:
            return None
        
        chunk_summaries = []
        print(f"  Processing {len(chunks)} chunks in batches of {batch_size}...")
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            print(f"  Summarizing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)...")
            
            batch_summaries = self._summarize_batch(
                batch,
                max_length=256,
                min_length=64
            )
            chunk_summaries.extend(batch_summaries)
        
        if not chunk_summaries:
            return None
        
        combined_summaries = " ".join(chunk_summaries)
        print(f"  Creating final summary from {len(chunk_summaries)} chunk summaries...")
        
        final_summary = self._summarize_single_text(
            combined_summaries,
            max_length=max_length,
            min_length=min_length
        )
        
        return final_summary
    
    def _summarize_batch(
        self,
        texts: List[str],
        max_length: int = 256,
        min_length: int = 64
    ) -> List[str]:
        if not texts:
            return []
        
        try:
            # Tokenize all texts in batch with dynamic padding
            inputs = self.tokenizer(
                texts,
                max_length=1024,
                truncation=True,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_length=max_length,
                    min_length=min_length,
                    num_beams=2,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    length_penalty=2.0
                )
            
            summaries = [
                self.post_process_summary(self.tokenizer.decode(summary_id, skip_special_tokens=True))
                for summary_id in summary_ids
            ]
            summaries = [s for s in summaries if s]
            return summaries
            
        except Exception as e:
            print(f"Error summarizing batch: {e}")
            return [self._summarize_single_text(text, max_length, min_length) or "" for text in texts]
    
    def _summarize_single_text(
        self,
        text: str,
        max_length: int = 256,
        min_length: int = 64
    ) -> Optional[str]:
        try:
            inputs = self.tokenizer(
                text,
                max_length=1024,
                truncation=True,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_length=max_length,
                    min_length=min_length,
                    num_beams=2,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    length_penalty=2.0
                )
            
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summary = self.post_process_summary(summary)
            return summary if summary else None
            
        except Exception as e:
            print(f"Error summarizing text: {e}")
            return None
    
    def summarize_paper(
        self,
        abstract: str,
        full_text: str,
        generate_abstract_summary: bool = True,
        generate_document_summary: bool = True
    ) -> Dict[str, Optional[str]]: 
        result = {
            'abstract_summary': None,
            'document_summary': None
        }
        
        if generate_abstract_summary and abstract:
            print("  Generating abstract summary...")
            result['abstract_summary'] = self.summarize_abstract(abstract)
        
        if generate_document_summary and full_text:
            print("  Generating document summary...")
            result['document_summary'] = self.summarize_long_document(
                full_text,
                max_length=1024,
                min_length=256
            )
            
            if result['abstract_summary'] and result['document_summary']:
                abstract_words = set(result['abstract_summary'].lower().split())
                doc_words = set(result['document_summary'].lower().split())
                similarity = len(abstract_words & doc_words) / max(len(abstract_words), len(doc_words), 1)
                
                if similarity > 0.7:
                    print(f"  Document summary too similar to abstract (similarity: {similarity:.2f}), regenerating...")
                    result['document_summary'] = self.summarize_long_document(
                        full_text,
                        max_length=1024,
                        min_length=200
                    )
        
        return result


_summarizer = None


def get_summarizer() -> PaperSummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = PaperSummarizer()
    return _summarizer
