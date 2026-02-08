"""
HTML Article Ingestion Module
Extracts text from HTML articles saved with SingleFile extension.
Parses URL from embedded comments and extracts author from filename.
Uses Cohere embed-english-v3.0 for embeddings with rate limit handling.
"""

import os
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
import uuid
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from backend.cohere_utils import cohere_embedder


class HTMLArticleIngester:
    """Handles ingestion of HTML articles into Qdrant."""
    
    def __init__(self):
        """Initialize the ingester with Cohere embedder and Qdrant client."""
        # Use shared cohere_embedder for rate limit handling
        self.embedder = cohere_embedder
        
        print(f"Connecting to Qdrant: {settings.QDRANT_URL}")
        self.qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        collections = self.qdrant.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if settings.QDRANT_COLLECTION_NAME not in collection_names:
            print(f"Creating collection: {settings.QDRANT_COLLECTION_NAME}")
            self.qdrant.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
        else:
            print(f"Collection already exists: {settings.QDRANT_COLLECTION_NAME}")

        # Ensure indexes exist for filtering
        self.qdrant.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            field_name="source_file",
            field_schema="keyword"
        )
        self.qdrant.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            field_name="resource_type",
            field_schema="keyword"
        )
    
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, str]:
        """
        Extract article title and author from filename.
        Expected format: "ArticleTitle-by-AuthorName.html"
        Falls back to extracting from HTML content if pattern not found.
        """
        basename = os.path.splitext(filename)[0]
        
        # Clean up common timestamp patterns from SingleFile
        # e.g., "Title (2_7_2026 9:28:44 AM)" -> "Title"
        basename = re.sub(r'\s*\([^)]*\d+[_/:]\d+[^)]*\)\s*$', '', basename)
        
        if "-by-" in basename.lower():
            # Split on -by- (case insensitive)
            parts = re.split(r'-by-', basename, flags=re.IGNORECASE)
            if len(parts) >= 2:
                return {
                    "article_title": parts[0].strip(),
                    "author": parts[1].strip()
                }
        
        return {
            "article_title": basename.strip(),
            "author": None  # Will be filled from HTML content
        }
    
    def extract_url_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract URL from SingleFile comment.
        SingleFile embeds: <!-- url: https://example.com -->
        """
        match = re.search(r'<!--[^>]*url:\s*(https?://[^\s]+)\s', html_content)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_author_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Try to extract author from HTML content.
        Looks for meta tags, bylines, or common author patterns.
        """
        # Check meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            prop = meta.get('property', '').lower()
            if name in ['author', 'article:author'] or prop in ['author', 'article:author']:
                author = meta.get('content')
                if author:
                    return author
        
        # Look for byline elements
        byline_selectors = [
            '.byline', '.author', '.post-author', 
            '[rel="author"]', '[itemprop="author"]'
        ]
        for selector in byline_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return None
    
    def extract_text_from_html(self, html_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from HTML file with metadata.
        Returns list of chunks with metadata.
        """
        all_chunks = []
        filename = os.path.basename(html_path)
        metadata = self.extract_metadata_from_filename(filename)
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract URL from SingleFile comment
            url = self.extract_url_from_html(html_content)
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract title from HTML if not in filename
            if not metadata.get("article_title") or metadata["article_title"] == filename.rsplit('.', 1)[0]:
                title_tag = soup.find('title')
                if title_tag:
                    metadata["article_title"] = title_tag.get_text(strip=True)
            
            # Extract author from HTML if not in filename
            if not metadata.get("author"):
                metadata["author"] = self.extract_author_from_html(soup) or "Unknown"
            
            print(f"  Processing: {metadata['article_title']} by {metadata['author']}")
            if url:
                print(f"    URL: {url}")
            
            # Remove script, style, and other non-content elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
                element.decompose()
            
            # Get main content - try common content containers first
            main_content = None
            for selector in ['article', 'main', '.content', '.post-content', '#content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Extract text paragraphs
            paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'li'])
            
            current_section = "Introduction"
            current_chunk = []
            current_length = 0
            
            for para in paragraphs:
                text = para.get_text(strip=True)
                if not text or len(text) < 10:
                    continue
                
                # Detect section headings
                if para.name in ['h1', 'h2', 'h3', 'h4']:
                    current_section = text[:100]
                    continue
                
                word_count = len(text.split())
                
                if current_length + word_count > settings.CHUNK_SIZE:
                    if current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        if len(chunk_text.strip()) > 50:
                            all_chunks.append({
                                "text": chunk_text,
                                "section_heading": current_section,
                                "resource_type": "article",
                                "article_title": metadata["article_title"],
                                "author": metadata["author"],
                                "url": url,
                                "exact_text": chunk_text,
                                "source_file": filename
                            })
                        
                        # Keep overlap
                        overlap_words = settings.CHUNK_OVERLAP
                        overlap_sentences = []
                        overlap_count = 0
                        for s in reversed(current_chunk):
                            s_words = len(s.split())
                            if overlap_count + s_words <= overlap_words:
                                overlap_sentences.insert(0, s)
                                overlap_count += s_words
                            else:
                                break
                        
                        current_chunk = overlap_sentences
                        current_length = overlap_count
                
                current_chunk.append(text)
                current_length += word_count
            
            # Don't forget the last chunk
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text.strip()) > 50:
                    all_chunks.append({
                        "text": chunk_text,
                        "section_heading": current_section,
                        "resource_type": "article",
                        "article_title": metadata["article_title"],
                        "author": metadata["author"],
                        "url": url,
                        "exact_text": chunk_text,
                        "source_file": filename
                    })
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  Error processing {html_path}: {e}")
            print(tb)
            raise Exception(f"{e}\n{tb}")
        
        return all_chunks
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for all chunks using Cohere with rate limit handling."""
        texts = [chunk["exact_text"] for chunk in chunks]
        print(f"    Generating Cohere embeddings for {len(texts)} chunks...")
        
        # Use rate-limited embedder
        return self.embedder.embed_documents(texts)
    
    def upload_to_qdrant(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Upload chunks with embeddings to Qdrant."""
        points = []
        
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "resource_type": chunk["resource_type"],
                    "article_title": chunk.get("article_title"),
                    "author": chunk.get("author"),
                    "url": chunk.get("url"),
                    "section_heading": chunk.get("section_heading"),
                    "exact_text": chunk["exact_text"],
                    "source_file": chunk.get("source_file")
                }
            )
            points.append(point)
        
        # Upload in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.qdrant.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=batch
            )
            print(f"    Uploaded batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
    
    def delete_article_vectors(self, filename: str):
        """Delete all vectors associated with a specific file."""
        print(f"    Deleting existing vectors for {filename}...")
        try:
            self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=filename)
                        ),
                        FieldCondition(
                            key="resource_type",
                            match=MatchValue(value="article")
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"    Error deleting vectors for {filename}: {e}")

    def ingest_article(self, html_path: str) -> int:
        """Full pipeline: extract, embed, upload a single HTML article."""
        # First, ensure idempotency by deleting any existing vectors for this file
        filename = os.path.basename(html_path)
        self.delete_article_vectors(filename)
        
        chunks = self.extract_text_from_html(html_path)
        
        if not chunks:
            print(f"  No chunks extracted from {html_path}")
            return 0
        
        embeddings = self.generate_embeddings(chunks)
        self.upload_to_qdrant(chunks, embeddings)
        
        return len(chunks)
    
    def ingest_all_articles(self, articles_dir: str) -> Dict[str, int]:
        """Ingest all HTML articles from a directory."""
        results = {}
        
        if not os.path.exists(articles_dir):
            print(f"Articles directory not found: {articles_dir}")
            return results
        
        html_files = [f for f in os.listdir(articles_dir) if f.lower().endswith('.html')]
        
        if not html_files:
            print(f"No HTML files found in {articles_dir}")
            return results
        
        print(f"Found {len(html_files)} HTML files to process")
        
        for html_file in html_files:
            html_path = os.path.join(articles_dir, html_file)
            chunk_count = self.ingest_article(html_path)
            results[html_file] = chunk_count
        
        return results


if __name__ == "__main__":
    # Direct execution for testing
    ingester = HTMLArticleIngester()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    articles_dir = os.path.join(project_root, settings.RESOURCES_ARTICLES_PATH)
    results = ingester.ingest_all_articles(articles_dir)
    
    print("\n=== Ingestion Complete ===")
    for file, count in results.items():
        print(f"  {file}: {count} chunks")
