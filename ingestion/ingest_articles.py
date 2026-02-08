"""
Article PDF Ingestion Module
Extracts text from article PDFs with section awareness and semantic chunking.
Uses Cohere embed-english-v3.0 for embeddings with rate limit handling.
"""

import os
import re
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
import uuid
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from backend.cohere_utils import cohere_embedder


class ArticleIngester:
    """Handles ingestion of article PDFs into Qdrant."""
    
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
        Extract article title and authors from filename.
        Expected format: "Title - Author.pdf" or just "Title.pdf"
        Also tries to extract URL if present in filename as "Title [URL].pdf"
        """
        basename = os.path.splitext(filename)[0]
        
        # Check for -by- pattern (case insensitive)
        if "-by-" in basename.lower():
            parts = re.split(r'-by-', basename, flags=re.IGNORECASE)
            if len(parts) >= 2:
                return {
                    "article_title": parts[0].strip(),
                    "authors": parts[1].strip(),
                    "url": None
                }
        
        # Try "Title - Author" pattern
        if " - " in basename:
            parts = basename.split(" - ", 1)
            return {
                "article_title": parts[0].strip(),
                "authors": parts[1].strip() if len(parts) > 1 else "Unknown",
                "url": None
            }
        
        return {
            "article_title": basename.strip(),
            "authors": "Unknown",
            "url": None
        }
    
    def detect_section_heading(self, text: str) -> Optional[str]:
        """
        Detect section headings in article text.
        Articles typically have sections like Abstract, Introduction, Methods, etc.
        """
        patterns = [
            r'^Abstract\s*$',
            r'^Introduction\s*$',
            r'^Background\s*$',
            r'^Methods?\s*$',
            r'^Methodology\s*$',
            r'^Results?\s*$',
            r'^Discussion\s*$',
            r'^Conclusion[s]?\s*$',
            r'^References\s*$',
            r'^\d+\.\s+[A-Z]',
            r'^[IVX]+\.\s+[A-Z]',
        ]
        
        for line in text.split('\n')[:10]:  # Check first 10 lines
            line = line.strip()
            for pattern in patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    return line[:100]
        
        return None
    
    def semantic_chunk_text(self, text: str, current_section: str) -> List[Dict[str, Any]]:
        """
        Split text into semantic chunks based on sentence boundaries.
        """
        chunks = []
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > settings.CHUNK_SIZE:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    if len(chunk_text.strip()) > 50:
                        chunks.append({
                            "text": chunk_text,
                            "section_heading": current_section
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
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Don't forget last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    "text": chunk_text,
                    "section_heading": current_section
                })
        
        return chunks
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from article PDF.
        Returns list of chunks with metadata.
        """
        all_chunks = []
        metadata = self.extract_metadata_from_filename(os.path.basename(pdf_path))
        current_section = "Introduction"
        
        print(f"  Processing: {metadata['article_title']}")
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Check for section heading
                detected_section = self.detect_section_heading(text)
                if detected_section:
                    current_section = detected_section
                
                # Create semantic chunks
                page_chunks = self.semantic_chunk_text(text, current_section)
                
                for chunk in page_chunks:
                    chunk.update({
                        "resource_type": "article",
                        "article_title": metadata["article_title"],
                        "authors": metadata["authors"],
                        "url": metadata.get("url"),
                        "exact_text": chunk["text"],
                        "source_file": os.path.basename(pdf_path)
                    })
                    all_chunks.append(chunk)
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  Error processing {pdf_path}: {e}")
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
                    "authors": chunk.get("authors"),
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

    def ingest_article(self, pdf_path: str) -> int:
        """Full pipeline: extract, embed, upload a single article."""
        # First, ensure idempotency by deleting any existing vectors for this file
        filename = os.path.basename(pdf_path)
        self.delete_article_vectors(filename)

        chunks = self.extract_text_from_pdf(pdf_path)
        
        if not chunks:
            print(f"  No chunks extracted from {pdf_path}")
            return 0
        
        embeddings = self.generate_embeddings(chunks)
        self.upload_to_qdrant(chunks, embeddings)
        
        return len(chunks)
    
    def ingest_all_articles(self, articles_dir: str) -> Dict[str, int]:
        """Ingest all PDF articles from a directory."""
        results = {}
        
        if not os.path.exists(articles_dir):
            print(f"Articles directory not found: {articles_dir}")
            return results
        
        pdf_files = [f for f in os.listdir(articles_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {articles_dir}")
            return results
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(articles_dir, pdf_file)
            chunk_count = self.ingest_article(pdf_path)
            results[pdf_file] = chunk_count
        
        return results


if __name__ == "__main__":
    # Direct execution for testing
    ingester = ArticleIngester()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    articles_dir = os.path.join(project_root, settings.RESOURCES_ARTICLES_PATH)
    results = ingester.ingest_all_articles(articles_dir)
    
    print("\n=== Ingestion Complete ===")
    for file, count in results.items():
        print(f"  {file}: {count} chunks")
