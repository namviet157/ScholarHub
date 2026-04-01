import re
from typing import List, Dict, Any, Tuple
from nltk.corpus import stopwords
from keybert import KeyBERT

class KeywordExtractor:
    """
    Extract keywords from scientific papers using KeyBERT.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', use_mmr: bool = True, diversity: float = 0.5):
        """
        Initialize keyword extractor.
        
        Args:
            model_name: Sentence transformer model for KeyBERT
            use_mmr: Use Maximal Marginal Relevance for diversity
            diversity: Diversity factor (0-1) for MMR
        """
        self.model_name = model_name
        self.use_mmr = use_mmr
        self.diversity = diversity
        self._keybert_model = None
        self._stop_words = set(stopwords.words('english'))
        
        # Add scientific paper specific stopwords
        self._stop_words.update({
            'paper', 'study', 'research', 'work', 'method', 'approach',
            'result', 'propose', 'show', 'present', 'using', 'based',
            'also', 'new', 'can', 'one', 'two', 'first', 'second',
            'however', 'therefore', 'thus', 'furthermore', 'moreover',
            'figure', 'table', 'equation', 'section', 'chapter',
            'use', 'used', 'uses', 'novel', 'significant', 'demonstrate',
            'achieves', 'performs', 'proposes', 'presents'
        })

        self.filter_words = {
            'revolutionized', 'demonstrates', 'achieves', 'proposes',
            'presents', 'combines', 'identifies', 'maintains'
        }
    
    def _lazy_load_keybert(self):
        """Lazy load KeyBERT model to avoid loading if not needed."""
        if self._keybert_model is None:
            self._keybert_model = KeyBERT(model=self.model_name)
        return self._keybert_model
    
    @staticmethod
    def clean_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        text = re.sub(r'http\S+|www\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'[^\w\s\-.,;:!?]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _is_valid_keyword(self, keyword: str, min_length: int = 3) -> bool:
        """Keyword validation."""
        keyword = keyword.strip().lower()
        
        if len(keyword) < min_length:
            return False
        
        if keyword in self._stop_words:
            return False
        
        if any(word in keyword.split() for word in self.filter_words):
            return False
        
        if not re.search(r'[a-zA-Z]', keyword):
            return False
        
        tokens = keyword.split()
        if all(len(token) <= 1 for token in tokens):
            return False
        
        meaningful_words = [w for w in tokens if w not in self._stop_words]
        if len(meaningful_words) == 0:
            return False
        
        return True

    def _remove_substrings(self, keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []
        phrases = [k['keyword'] for k in keywords]
        for kw in keywords:
            if not any(kw['keyword'] != other and kw['keyword'] in other for other in phrases):
                cleaned.append(kw)
        return cleaned
    
    def extract_keybert(self,
                       text: str,
                       top_n: int = 10,
                       ngram_range: Tuple[int, int] = (1, 2),
                       min_length: int = 3) -> List[Dict[str, Any]]:
        """
        Extract keywords using KeyBERT.
        
        Args:
            text: Input text
            top_n: Number of keywords to extract
            ngram_range: Range of n-grams to consider
            min_length: Minimum keyword length
            
        Returns:
            List of dictionaries with 'keyword' and 'score'
        """
        cleaned_text = self.clean_text(text)
        if not cleaned_text or len(cleaned_text.split()) < 10:
            return []
        
        try:
            model = self._lazy_load_keybert()
            
            keywords_with_scores = model.extract_keywords(
                cleaned_text,
                keyphrase_ngram_range=ngram_range,
                stop_words=list(self._stop_words),
                top_n=top_n * 3,
                use_mmr=self.use_mmr,
                diversity=self.diversity if self.use_mmr else None
            )
            
            keywords = []
            seen = set()
            
            for keyword, score in keywords_with_scores:
                keyword = keyword.strip().lower()
                
                if self._is_valid_keyword(keyword, min_length=min_length) and keyword not in seen:
                    if ' '.join(reversed(keyword.split())) in seen:
                        continue
                    keywords.append({
                        'keyword': keyword,
                        'score': float(score),
                        'method': 'keybert'
                    })
                    seen.add(keyword)
                
            keywords = self._remove_substrings(keywords)
            return keywords[:top_n]
            
        except Exception as e:
            print(f"Error in KeyBERT extraction: {e}")
            return []
    
    def extract_from_paper(self,
                          abstract: str,
                          full_text: str = "",
                          title: str = "",
                          top_n: int = 10,
                          ngram_range: Tuple[int, int] = (1, 2)) -> List[Dict[str, Any]]:
        """
        Extract keywords from a complete paper.
        
        Args:
            abstract: Paper abstract
            full_text: Full paper text (optional)
            title: Paper title (optional)
            top_n: Number of keywords to extract
            ngram_range: N-gram range
            
        Returns:
            List of keyword dictionaries
        """
        text_parts = []
        
        if title:
            text_parts.extend([title] * 3)
        
        if abstract:
            text_parts.extend([abstract] * 2)
        
        if full_text:
            words = full_text.split()[:5000]
            text_parts.append(' '.join(words))
        
        combined_text = ' '.join(text_parts)
        
        return self.extract_keybert(combined_text, top_n=top_n, ngram_range=ngram_range)
        
def get_keyword_extractor(model_name: str = 'all-MiniLM-L6-v2') -> KeywordExtractor:
    """
    Get a singleton instance of KeywordExtractor.
    
    Args:
        model_name: Sentence transformer model name
        
    Returns:
        KeywordExtractor instance
    """
    if not hasattr(get_keyword_extractor, '_instance'):
        get_keyword_extractor._instance = KeywordExtractor(model_name=model_name)
    return get_keyword_extractor._instance