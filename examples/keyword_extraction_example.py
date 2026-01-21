"""
Example: Keyword Extraction from Scientific Papers

This example demonstrates how to use the keyword extraction module
to extract relevant keywords from scientific paper text.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processing.keywords_extraction import KeywordExtractor


def example_1_basic_extraction():
    """Example 1: Basic keyword extraction from text."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Keyword Extraction")
    print("=" * 80)
    
    text = """
    Artificial intelligence and machine learning have transformed the field of 
    computer vision. Deep convolutional neural networks (CNNs) have achieved 
    remarkable performance on image classification tasks. Recent advances in 
    attention mechanisms and transformer architectures have further improved 
    model accuracy and efficiency.
    """
    
    extractor = KeywordExtractor()
    
    # Extract using KeyBERT
    keywords = extractor.extract_keybert(text, top_n=5)
    
    print("\nExtracted Keywords (KeyBERT):")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw['keyword']} (score: {kw['score']:.3f})")


def example_2_compare_methods():
    """Example 2: Compare TF-IDF and KeyBERT methods."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Comparing TF-IDF vs KeyBERT")
    print("=" * 80)
    
    abstract = """
    We propose a novel graph neural network architecture for molecular property 
    prediction. Our model leverages message passing algorithms to aggregate 
    information from neighboring atoms, combined with attention mechanisms to 
    weight the importance of different molecular substructures. Experiments on 
    benchmark datasets demonstrate superior performance compared to traditional 
    fingerprint-based methods and other graph-based approaches.
    """
    
    extractor = KeywordExtractor()
    
    # KeyBERT
    keybert_kw = extractor.extract_keybert(abstract, top_n=5)
    print("\nKeyBERT Keywords:")
    for kw in keybert_kw:
        print(f"  • {kw['keyword']} (score: {kw['score']:.3f})")


def example_3_full_paper():
    """Example 3: Extract from complete paper (title + abstract + text)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Full Paper Keyword Extraction")
    print("=" * 80)
    
    title = "Attention Is All You Need: Transformer Architecture for NLP"
    
    abstract = """
    The dominant sequence transduction models are based on complex recurrent or 
    convolutional neural networks that include an encoder and a decoder. The best 
    performing models also connect the encoder and decoder through an attention 
    mechanism. We propose a new simple network architecture, the Transformer, 
    based solely on attention mechanisms, dispensing with recurrence and 
    convolutions entirely.
    """
    
    full_text = """
    The Transformer architecture has revolutionized natural language processing 
    by introducing multi-head self-attention as the core building block. Unlike 
    recurrent neural networks (RNNs) and long short-term memory (LSTM) networks, 
    transformers process sequences in parallel, significantly reducing training time.
    
    The model uses positional encodings to inject information about the position 
    of tokens in the sequence. Multi-head attention allows the model to jointly 
    attend to information from different representation subspaces at different 
    positions. Feed-forward networks are applied to each position separately and 
    identically. Layer normalization and residual connections help stabilize training.
    
    We evaluate our model on machine translation tasks and achieve state-of-the-art 
    results on the WMT 2014 English-to-German and English-to-French translation 
    benchmarks. The Transformer architecture has since been adapted for various 
    other NLP tasks including language modeling, question answering, and text 
    classification.
    """
    
    extractor = KeywordExtractor()
    
    # Extract using KeyBERT
    keywords = extractor.extract_from_paper(
        title=title,
        abstract=abstract,
        full_text=full_text,
        top_n=8
    )
    
    print("\nKeyBERT Keywords (Title + Abstract + Full Text):\n")
    print(f"{'Rank':<6} {'Keyword':<35} {'KeyBERT':<10}")
    print("-" * 75)
    
    for i, kw in enumerate(keywords, 1):
        print(f"{i:<6} {kw['keyword']:<35} "
              f"{kw.get('score', 0):<10.3f}")


def example_4_customize_parameters():
    """Example 4: Customize extraction parameters."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Customizing Extraction Parameters")
    print("=" * 80)
    
    text = """
    Climate change poses significant challenges to global food security. 
    Agricultural systems must adapt to changing temperature patterns, 
    precipitation variability, and extreme weather events. Sustainable 
    farming practices, precision agriculture technologies, and crop 
    breeding programs are essential for building resilience.
    """
    
    extractor = KeywordExtractor(
        model_name='all-MiniLM-L6-v2',
        use_mmr=True,
        diversity=0.7
    )
    
    # Extract using KeyBERT
    keywords = extractor.extract_keybert(
        text=text,
        top_n=6,
        ngram_range=(1, 4),
        min_length=5
    )
    
    print("\nCustomized Keywords (high diversity, 1-4 word phrases):")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw['keyword']} ({len(kw['keyword'].split())} words, "
              f"score: {kw['score']:.3f})")


def example_5_multilingual():
    """Example 5: Multilingual keyword extraction (if using multilingual model)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Multilingual Support")
    print("=" * 80)
    
    vietnamese_text = """
    Trí tuệ nhân tạo và học máy đã thay đổi cách chúng ta xử lý dữ liệu và 
    giải quyết các vấn đề phức tạp. Mạng nơ-ron sâu và các thuật toán học sâu 
    đã đạt được những thành tựu đáng kể trong nhận dạng hình ảnh, xử lý ngôn 
    ngữ tự nhiên và nhiều lĩnh vực khác.
    """
    
    extractor = KeywordExtractor(
        model_name='paraphrase-multilingual-MiniLM-L12-v2'
    )
    
    # Extract using KeyBERT
    keywords = extractor.extract_keybert(vietnamese_text, top_n=5)
    
    print("\nVietnamese Keywords:")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw['keyword']} (score: {kw['score']:.3f})")

def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("KEYWORD EXTRACTION EXAMPLES")
    print("=" * 80)
    
    try:
        example_1_basic_extraction()
        example_2_compare_methods()
        example_3_full_paper()
        example_4_customize_parameters()
        example_5_multilingual()
        
        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED!")
        print("=" * 80)
        print("\nCheck KEYWORDS_README.md for more information.\n")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
