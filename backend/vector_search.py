"""
Vector Search Module
Handles all Qdrant operations for similarity search.
Enhanced with Perplexity-style RAG techniques:
- Multi-query expansion
- Result merging and deduplication
- Cohere reranking with rate limit handling
- Source diversity

Uses Cohere embed-english-v3.0 for query embeddings and rerank-english-v3.0 for reranking.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from backend.cohere_utils import cohere_embedder


class VectorSearch:
    """Handles vector similarity search against Qdrant with enhanced RAG techniques."""
    
    _instance = None
    _qdrant_client = None
    
    def __new__(cls):
        """Singleton pattern to avoid reloading clients."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Cohere embedder and Qdrant client."""
        # Use shared cohere_embedder for rate limit handling
        self.embedder = cohere_embedder
        
        if VectorSearch._qdrant_client is None:
            print(f"Connecting to Qdrant: {settings.QDRANT_URL}", flush=True)
            VectorSearch._qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
    
    @property
    def qdrant(self):
        return VectorSearch._qdrant_client
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string using Cohere with search_query input type."""
        return self.embedder.embed_query(query)
    
    def _single_query_search(
        self,
        query: str,
        limit: int,
        search_filter: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """Perform a single vector search."""
        query_embedding = self.embed_query(query)
        return self._search_with_embedding(query_embedding, limit, search_filter)
    
    def _search_with_embedding(
        self,
        query_embedding: List[float],
        limit: int,
        search_filter: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search with a pre-computed embedding."""
        try:
            results = self.qdrant.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter,
                score_threshold=settings.SIMILARITY_THRESHOLD
            )
        except Exception as e:
            print(f"Search error: {e}", flush=True)
            return []
        
        chunks = []
        for result in results:
            payload = result.payload
            chunk = {
                "score": result.score,
                "resource_type": payload.get("resource_type"),
                "source_file": payload.get("source_file"),
                "exact_text": payload.get("exact_text"),
                "book_title": payload.get("book_title"),
                "author": payload.get("author"),
                "page_number": payload.get("page_number"),
                "chapter": payload.get("chapter"),
                "article_title": payload.get("article_title"),
                "authors": payload.get("authors"),
                "url": payload.get("url"),
                "section_heading": payload.get("section_heading"),
            }
            chunks.append(chunk)
        
        return chunks
    
    def _merge_results(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge results from multiple queries.
        Uses text hash for deduplication and averages scores for duplicates.
        """
        seen_texts = {}
        
        for chunk in all_results:
            text = chunk.get("exact_text", "")
            text_hash = hash(text[:200])  # Use first 200 chars for matching
            
            if text_hash in seen_texts:
                # Average the scores
                existing = seen_texts[text_hash]
                existing["score"] = (existing["score"] + chunk["score"]) / 2
                existing["match_count"] = existing.get("match_count", 1) + 1
            else:
                chunk["match_count"] = 1
                seen_texts[text_hash] = chunk
        
        # Sort by match_count (multi-query hits) then by score
        merged = list(seen_texts.values())
        merged.sort(key=lambda x: (x.get("match_count", 1), x["score"]), reverse=True)
        
        return merged
    
    def _rerank_with_cohere(
        self,
        original_query: str,
        chunks: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using Cohere rerank-english-v3.0 with rate limit handling.
        Cohere's reranker uses cross-attention for much better relevance than bi-encoders.
        """
        if not settings.ENABLE_RERANKING or not chunks:
            return chunks[:top_k]
        
        # Prepare documents for reranking
        documents = [chunk.get("exact_text", "") for chunk in chunks]
        
        try:
            # Use rate-limited embedder for reranking
            response = self.embedder.rerank(
                query=original_query,
                documents=documents,
                top_n=min(top_k, len(documents))
            )
            
            # Map rerank results back to chunks
            reranked_chunks = []
            for result in response.results:
                chunk = chunks[result.index].copy()
                chunk["rerank_score"] = result.relevance_score
                reranked_chunks.append(chunk)
            
            self._log(f"  Reranked {len(chunks)} results with Cohere")
            
            return reranked_chunks
            
        except Exception as e:
            self._log(f"  Reranking failed, using original order: {e}")
            return chunks[:top_k * 2]
    
    def _apply_diversity(self, chunks: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """
        Apply source diversity using round-robin selection across sources.
        Ensures results come from multiple books/articles.
        """
        if not chunks:
            return []
        
        # Preserve absolute top 3 results regardless of diversity (Best Evidence Rule)
        # This ensures that if one book has the perfect answer, we see multiple chunks from it.
        top_absolute = chunks[:3]
        remaining = chunks[3:]
        
        # Apply diversity to the rest
        diverse_pool = []
        if remaining:
            # Group by source
            groups = defaultdict(list)
            for chunk in remaining:
                key = chunk.get("source_file") or chunk.get("book_title") or chunk.get("article_title") or "unknown"
                groups[key].append(chunk)
            
            # Round-robin selection
            keys = list(groups.keys())
            while len(diverse_pool) < (top_k - 3) and any(groups.values()):
                for key in keys:
                    if groups[key] and len(diverse_pool) < (top_k - 3):
                        diverse_pool.append(groups[key].pop(0))
        
        # Combine top absolute + diverse pool
        final_results = top_absolute + diverse_pool
        
        return final_results

    def search(
        self,
        query: str,
        top_k: int = None,
        resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced search with multi-query expansion, reranking, and diversity.
        
        This implements Perplexity-style RAG 2.0 techniques:
        1. Expand query into multiple variations
        2. Search with each variation
        3. Merge and deduplicate results
        4. Rerank with Cohere rerank-english-v3.0
        5. Apply source diversity
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        self._log(f"\n{'='*50}")
        self._log(f"[SEARCH] Enhanced RAG Search with Cohere")
        self._log(f"  Original query: {query[:80]}...")
        
        # Build filter if resource_type specified
        search_filter = None
        if resource_type:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="resource_type",
                        match=MatchValue(value=resource_type)
                    )
                ]
            )
        
        # Import query processor
        try:
            from backend.query_processor import expand_query
            queries = expand_query(query)
        except ImportError:
            queries = [query]
        
        self._log(f"  Expanded to {len(queries)} query variations")
        
        # Batch embed all queries in one Cohere API call
        all_embeddings = self.embedder.embed_queries(queries)
        self._log(f"  Batch embedded {len(queries)} queries in one call")
        
        # Search with each pre-computed embedding
        all_results = []
        fetch_limit = top_k * 2  # Reduced fetch volume
        
        for i, (q, emb) in enumerate(zip(queries, all_embeddings)):
            results = self._search_with_embedding(emb, fetch_limit, search_filter)
            all_results.extend(results)
            self._log(f"    Query {i+1}: {len(results)} results")
        
        self._log(f"  Total raw results: {len(all_results)}")
        
        # Merge and deduplicate
        merged = self._merge_results(all_results)
        self._log(f"  After merge/dedup: {len(merged)}")
        
        # Rerank with Cohere
        reranked = self._rerank_with_cohere(query, merged, top_k)
        
        # Apply diversity
        final_results = self._apply_diversity(reranked, top_k)
        
        self._log(f"  Final results: {len(final_results)}")
        
        # Log top retrieved chunks for debugging
        self._log(f"\n[RAG] Top {min(5, len(final_results))} Retrieved Chunks (sent to LLM):")
        for i, chunk in enumerate(final_results[:5]):
            source = chunk.get('source_file') or chunk.get('book_title') or chunk.get('article_title') or 'Unknown'
            # Preview content (first 100 chars, no newlines)
            content_preview = (chunk.get('exact_text') or '')[:100].replace('\n', ' ')
            score = chunk.get('score', 0)
            self._log(f"  {i+1}. [{score:.4f}] {source} - \"{content_preview}...\"")

        self._log(f"{'='*50}\n")
        
        return final_results
    
    def _log(self, message: str):
        """Log directly to stdout to bypass buffering/capture."""
        try:
            sys.stdout.write(message + "\n")
            sys.stdout.flush()
        except Exception:
            print(message, flush=True)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            collection_info = self.qdrant.get_collection(settings.QDRANT_COLLECTION_NAME)
            return {
                "exists": True,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status.value
            }
        except Exception as e:
            return {
                "exists": False,
                "error": str(e)
            }


# Global instance
vector_search = VectorSearch()


def search_resources(query: str, top_k: int = None) -> List[Dict[str, Any]]:
    """Convenience function for searching."""
    return vector_search.search(query, top_k)
