"""
Cohere Client Utility
Provides a shared Cohere client with rate limit handling for embeddings.
Implements exponential backoff with retry logic for trial API limits.
"""

import time
import cohere
from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings


class CohereEmbedder:
    """Handles Cohere embeddings with rate limit handling."""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Cohere client."""
        if CohereEmbedder._client is None:
            print(f"Initializing Cohere client for model: {settings.EMBEDDING_MODEL}")
            CohereEmbedder._client = cohere.Client(settings.COHERE_API_KEY)
    
    @property
    def client(self):
        return CohereEmbedder._client
    
    def embed_documents(
        self,
        texts: List[str],
        batch_size: int = 96,
        max_retries: int = 5,
        initial_wait: float = 60.0
    ) -> List[List[float]]:
        """
        Generate embeddings for documents with rate limit handling.
        
        Args:
            texts: List of texts to embed
            batch_size: Maximum batch size (Cohere limit is 96)
            max_retries: Maximum number of retries per batch on rate limit
            initial_wait: Initial wait time in seconds on rate limit (will double each retry)
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        total_batches = (len(texts) - 1) // batch_size + 1
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            print(f"      Processing batch {batch_num}/{total_batches}...")
            
            embeddings = self._embed_batch_with_retry(
                batch,
                input_type="search_document",
                max_retries=max_retries,
                initial_wait=initial_wait
            )
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def embed_query(self, query: str, max_retries: int = 3, initial_wait: float = 10.0) -> List[float]:
        """
        Generate embedding for a single query with rate limit handling.
        Uses input_type="search_query" for asymmetric search.
        """
        embeddings = self._embed_batch_with_retry(
            [query],
            input_type="search_query",
            max_retries=max_retries,
            initial_wait=initial_wait
        )
        return embeddings[0]
    
    def _embed_batch_with_retry(
        self,
        texts: List[str],
        input_type: str,
        max_retries: int,
        initial_wait: float
    ) -> List[List[float]]:
        """Embed a batch with exponential backoff on rate limits."""
        wait_time = initial_wait
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.embed(
                    texts=texts,
                    model=settings.EMBEDDING_MODEL,
                    input_type=input_type
                )
                return response.embeddings
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if "429" in str(e) or "rate limit" in error_str or "too many" in error_str:
                    if attempt < max_retries:
                        print(f"        Rate limited. Waiting {wait_time:.0f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        wait_time *= 2  # Exponential backoff
                        continue
                    else:
                        raise Exception(f"Max retries exceeded due to rate limits: {e}")
                else:
                    # Non-rate-limit error, raise immediately
                    raise
        
        raise Exception("Unexpected state in retry loop")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = None,
        max_retries: int = 3,
        initial_wait: float = 10.0
    ):
        """
        Rerank documents with rate limit handling.
        """
        wait_time = initial_wait
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.rerank(
                    query=query,
                    documents=documents,
                    model=settings.RERANKER_MODEL,
                    top_n=top_n or len(documents)
                )
                return response
                
            except Exception as e:
                error_str = str(e).lower()
                
                if "429" in str(e) or "rate limit" in error_str or "too many" in error_str:
                    if attempt < max_retries:
                        print(f"        Rerank rate limited. Waiting {wait_time:.0f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        wait_time *= 2
                        continue
                    else:
                        raise Exception(f"Max retries exceeded due to rate limits: {e}")
                else:
                    raise
        
        raise Exception("Unexpected state in retry loop")


# Singleton instance
cohere_embedder = CohereEmbedder()
