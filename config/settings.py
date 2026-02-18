"""
FounderGPT Configuration Settings
All environment variables and configuration in one place.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Claude API Configuration (loaded from .env)
    CLAUDE_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    
    # OpenAI Configuration (loaded from .env)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1"

    # Gemini Configuration (loaded from .env)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Cohere Configuration (loaded from .env)
    COHERE_API_KEY: str
    
    # Qdrant Configuration (loaded from .env)
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "startup_guru_resources"
    
    # Embedding Configuration (Cohere embed-english-v3.0)
    EMBEDDING_MODEL: str = "embed-english-v3.0"
    EMBEDDING_DIMENSION: int = 1024
    
    # Chunking Configuration
    CHUNK_SIZE: int = 700  # Target tokens per chunk
    CHUNK_OVERLAP: int = 140  # Overlap tokens
    
    # Paths
    RESOURCES_BOOKS_PATH: str = "resources/books"
    RESOURCES_ARTICLES_PATH: str = "resources/articles"
    PROCESSED_FILES_PATH: str = ".processed_files.json"
    RESOURCES_INDEX_FILE: str = "config/resources_index.json"
    
    # Vector Search - Enhanced RAG Settings
    TOP_K_RESULTS: int = 6  # Reduced from 10 — model only cites 2-3 per question
    SIMILARITY_THRESHOLD: float = 0.28  # Lowered to capture more relevant usage
    
    # Cohere Reranker
    RERANKER_MODEL: str = "rerank-english-v3.0"
    ENABLE_RERANKING: bool = True
    
    # Query Expansion
    ENABLE_QUERY_EXPANSION: bool = True
    
    # Retrieval Configuration
    INITIAL_RETRIEVAL_MULTIPLIER: int = 3  # Fetch 3x chunks initially before reranking
    
    # Admin Configuration (loaded from .env)
    ADMIN_PASSWORD: str
    
    # Categories Configuration
    CATEGORIES_FILE: str = "config/categories.json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

