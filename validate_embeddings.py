"""
Validation script for semantic search quality.
Tests embeddings at different levels and provides quality metrics.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from processing.embeddings import get_embedding_service
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("DOCUMENT_CONTENTS_COLLECTION")

if MONGO_URL and DATABASE_NAME and COLLECTION_NAME:
    client = MongoClient(MONGO_URL)
    db = client[DATABASE_NAME]
    mongo_collection = db[COLLECTION_NAME]
else:
    mongo_collection = None


class EmbeddingValidator:
    """Validate semantic search quality."""
    
    def __init__(self):
        """Initialize validator."""
        self.service = get_embedding_service()
        self.test_queries = [
            {
                "query": "machine learning algorithms",
                "expected_topics": ["neural networks", "deep learning", "supervised learning", "classification"],
                "level": "paper"
            },
            {
                "query": "transformer architecture attention mechanism",
                "expected_topics": ["BERT", "GPT", "self-attention", "encoder-decoder"],
                "level": "section"
            },
            {
                "query": "gradient descent optimization",
                "expected_topics": ["backpropagation", "learning rate", "stochastic", "adam"],
                "level": "chunk"
            },
            {
                "query": "natural language processing",
                "expected_topics": ["NLP", "text processing", "language models", "tokenization"],
                "level": "paper"
            },
            {
                "query": "experimental results performance metrics",
                "expected_topics": ["accuracy", "F1 score", "evaluation", "benchmark"],
                "level": "section"
            },
            {
                "query": "convolutional neural networks image recognition",
                "expected_topics": ["CNN", "convolution", "image classification", "feature extraction"],
                "level": "chunk"
            }
        ]
    
    def calculate_relevance_score(self, result: Dict[str, Any], query: str, expected_topics: List[str]) -> float:
        """
        Calculate relevance score for a search result.
        
        Args:
            result: Search result dictionary
            query: Original query
            expected_topics: Expected topics/keywords
        
        Returns:
            Relevance score between 0 and 1
        """
        metadata = result.get('metadata', {})
        text = ""
        
        # Extract text from metadata based on level
        if 'abstract' in metadata:
            text = metadata.get('abstract', '')
        elif 'text' in metadata:
            text = metadata.get('text', '')
        elif 'section_title' in metadata:
            text = metadata.get('section_title', '') + " " + metadata.get('text', '')
        
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Check for query term matches
        query_terms = query_lower.split()
        matches = sum(1 for term in query_terms if term in text_lower)
        query_score = matches / len(query_terms) if query_terms else 0
        
        # Check for expected topic matches
        topic_matches = sum(1 for topic in expected_topics if topic.lower() in text_lower)
        topic_score = min(topic_matches / len(expected_topics), 1.0) if expected_topics else 0
        
        # Combine scores (weighted average)
        relevance = 0.6 * query_score + 0.4 * topic_score
        
        return relevance
    
    def validate_query(self, test_case: Dict[str, Any], k: int = 10) -> Dict[str, Any]:
        """
        Validate a single query.
        
        Args:
            test_case: Test case dictionary with query, expected_topics, level
            k: Number of results to retrieve
        
        Returns:
            Validation results dictionary
        """
        query = test_case["query"]
        expected_topics = test_case.get("expected_topics", [])
        level = test_case.get("level", "chunk")
        
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Level: {level}")
        print(f"{'='*60}")
        
        # Perform search
        results = self.service.search(query, level=level, k=k)
        
        if not results:
            return {
                "query": query,
                "level": level,
                "num_results": 0,
                "avg_relevance": 0.0,
                "top_5_avg_relevance": 0.0,
                "results": []
            }
        
        # Calculate relevance scores
        relevance_scores = []
        detailed_results = []
        
        for i, result in enumerate(results):
            relevance = self.calculate_relevance_score(result, query, expected_topics)
            relevance_scores.append(relevance)
            
            metadata = result.get('metadata', {})
            detailed_results.append({
                "rank": i + 1,
                "score": result.get('score', 0),
                "relevance": relevance,
                "paper_id": metadata.get('paper_id', 'unknown'),
                "preview": metadata.get('text', metadata.get('abstract', ''))[:200]
            })
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        top_5_avg = sum(relevance_scores[:5]) / min(5, len(relevance_scores)) if relevance_scores else 0
        
        return {
            "query": query,
            "level": level,
            "num_results": len(results),
            "avg_relevance": avg_relevance,
            "top_5_avg_relevance": top_5_avg,
            "results": detailed_results
        }
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all test queries."""
        print("Starting embedding validation...")
        print(f"Total test queries: {len(self.test_queries)}")
        
        results = []
        for test_case in self.test_queries:
            result = self.validate_query(test_case)
            results.append(result)
            
            # Print summary
            print(f"\n  Results: {result['num_results']}")
            print(f"  Average Relevance: {result['avg_relevance']:.3f}")
            print(f"  Top 5 Average Relevance: {result['top_5_avg_relevance']:.3f}")
            
            # Show top 3 results
            print("\n  Top 3 Results:")
            for res in result['results'][:3]:
                print(f"    [{res['rank']}] Score: {res['score']:.3f}, Relevance: {res['relevance']:.3f}")
                print(f"        Paper: {res['paper_id']}")
                print(f"        Preview: {res['preview'][:100]}...")
        
        # Calculate overall statistics
        all_relevances = []
        all_top_5_relevances = []
        
        for result in results:
            if result['num_results'] > 0:
                all_relevances.append(result['avg_relevance'])
                all_top_5_relevances.append(result['top_5_avg_relevance'])
        
        overall_stats = {
            "total_queries": len(results),
            "successful_queries": len([r for r in results if r['num_results'] > 0]),
            "overall_avg_relevance": sum(all_relevances) / len(all_relevances) if all_relevances else 0,
            "overall_top_5_avg_relevance": sum(all_top_5_relevances) / len(all_top_5_relevances) if all_top_5_relevances else 0,
            "results_by_level": {}
        }
        
        # Group by level
        for level in ["paper", "section", "chunk"]:
            level_results = [r for r in results if r['level'] == level]
            if level_results:
                level_relevances = [r['avg_relevance'] for r in level_results if r['num_results'] > 0]
                overall_stats["results_by_level"][level] = {
                    "num_queries": len(level_results),
                    "avg_relevance": sum(level_relevances) / len(level_relevances) if level_relevances else 0
                }
        
        return {
            "overall_stats": overall_stats,
            "query_results": results
        }
    
    def test_specific_paper(self, paper_id: str, query: str, level: str = "chunk", k: int = 5):
        """
        Test search for a specific paper.
        
        Args:
            paper_id: ArXiv ID of the paper
            query: Search query
            level: Embedding level
            k: Number of results
        """
        print(f"\n{'='*60}")
        print(f"Testing search for paper: {paper_id}")
        print(f"Query: {query}")
        print(f"Level: {level}")
        print(f"{'='*60}")
        
        results = self.service.search(query, level=level, k=k)
        
        # Filter results for this paper
        paper_results = [r for r in results if r.get('metadata', {}).get('paper_id') == paper_id]
        
        print(f"\nTotal results: {len(results)}")
        print(f"Results for paper {paper_id}: {len(paper_results)}")
        
        if paper_results:
            print("\nResults for this paper:")
            for i, result in enumerate(paper_results):
                metadata = result.get('metadata', {})
                print(f"\n  [{i+1}] Score: {result.get('score', 0):.3f}")
                print(f"      Section: {metadata.get('section_title', 'N/A')}")
                print(f"      Preview: {metadata.get('text', '')[:200]}...")
        else:
            print("\nNo results found for this paper.")
            print("\nTop results overall:")
            for i, result in enumerate(results[:3]):
                metadata = result.get('metadata', {})
                print(f"\n  [{i+1}] Score: {result.get('score', 0):.3f}")
                print(f"      Paper: {metadata.get('paper_id', 'unknown')}")
                print(f"      Preview: {metadata.get('text', metadata.get('abstract', ''))[:200]}...")
    
    def generate_report(self, output_path: Path = None):
        """Generate validation report."""
        if output_path is None:
            output_path = Path(__file__).parent / "embedding_validation_report.json"
        
        validation_results = self.validate_all()
        
        # Save to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        stats = validation_results['overall_stats']
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Successful Queries: {stats['successful_queries']}")
        print(f"Overall Average Relevance: {stats['overall_avg_relevance']:.3f}")
        print(f"Overall Top 5 Average Relevance: {stats['overall_top_5_avg_relevance']:.3f}")
        
        print("\nResults by Level:")
        for level, level_stats in stats['results_by_level'].items():
            print(f"  {level.capitalize()}:")
            print(f"    Queries: {level_stats['num_queries']}")
            print(f"    Avg Relevance: {level_stats['avg_relevance']:.3f}")
        
        print(f"\nFull report saved to: {output_path}")
        
        return validation_results


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate semantic search embeddings")
    parser.add_argument("--query", type=str, help="Test a specific query")
    parser.add_argument("--level", type=str, choices=["paper", "section", "chunk"], default="chunk",
                       help="Embedding level to test")
    parser.add_argument("--paper-id", type=str, help="Test search for a specific paper")
    parser.add_argument("--k", type=int, default=10, help="Number of results to retrieve")
    parser.add_argument("--report", action="store_true", help="Generate full validation report")
    
    args = parser.parse_args()
    
    validator = EmbeddingValidator()
    
    if args.paper_id and args.query:
        # Test specific paper
        validator.test_specific_paper(args.paper_id, args.query, args.level, args.k)
    elif args.query:
        # Test single query
        test_case = {
            "query": args.query,
            "expected_topics": [],
            "level": args.level
        }
        result = validator.validate_query(test_case, args.k)
        print(f"\nValidation Result:")
        print(f"  Results: {result['num_results']}")
        print(f"  Average Relevance: {result['avg_relevance']:.3f}")
    else:
        # Generate full report
        validator.generate_report()


if __name__ == "__main__":
    main()
