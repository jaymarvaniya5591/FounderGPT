"""
Book PDF Ingestion Module
Extracts text from book PDFs with page awareness and semantic chunking.
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


class BookIngester:
    """Handles ingestion of book PDFs into Qdrant."""
    
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
        Extract book title and author from filename.
        Expected format: "Title-by-Author.pdf" (uses -by- separator)
        Falls back to "Unknown" author if pattern not found.
        """
        basename = os.path.splitext(filename)[0]
        
        # Check for -by- pattern (case insensitive)
        if "-by-" in basename.lower():
            # Split on -by- (case insensitive)
            parts = re.split(r'-by-', basename, flags=re.IGNORECASE)
            if len(parts) >= 2:
                return {
                    "book_title": parts[0].strip(),
                    "author": parts[1].strip()
                }
        
        return {
            "book_title": basename.strip(),
            "author": "Unknown"
        }
    
    def detect_chapter(self, text: str, page_num: int) -> Optional[str]:
        """
        Detect chapter headings in text.
        Looks for common patterns like "Chapter 1", "CHAPTER ONE", etc.
        """
        patterns = [
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+\d+',
            r'^Chapter\s+[A-Z][a-z]+',
            r'^PART\s+[IVX]+',
            r'^Part\s+\d+',
            r'^\d+\.\s+[A-Z]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                # Get the full line as chapter title
                line_start = text.rfind('\n', 0, match.start()) + 1
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)
                return text[line_start:line_end].strip()[:100]  # Limit length
        
        return None
    
    def semantic_chunk_text(self, text: str, page_num: int, current_chapter: str) -> List[Dict[str, Any]]:
        """
        Split text into semantic chunks based on sentence boundaries.
        Maintains context with overlap.
        """
        chunks = []
        
        # Split into sentences (approximate)
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
                    if len(chunk_text.strip()) > 50:  # Minimum chunk size
                        chunks.append({
                            "text": chunk_text,
                            "page_number": page_num,
                            "chapter": current_chapter
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
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    "text": chunk_text,
                    "page_number": page_num,
                    "chapter": current_chapter
                })
        
        return chunks
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF with page awareness.
        Returns list of chunks with metadata.
        """
        all_chunks = []
        metadata = self.extract_metadata_from_filename(os.path.basename(pdf_path))
        current_chapter = "Introduction"
        
        print(f"  Processing: {metadata['book_title']} by {metadata['author']}")
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Check for chapter heading
                detected_chapter = self.detect_chapter(text, page_num)
                if detected_chapter:
                    current_chapter = detected_chapter
                
                # Create semantic chunks
                page_chunks = self.semantic_chunk_text(text, page_num, current_chapter)
                
                for chunk in page_chunks:
                    chunk.update({
                        "resource_type": "book",
                        "book_title": metadata["book_title"],
                        "author": metadata["author"],
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
                    "book_title": chunk.get("book_title"),
                    "author": chunk.get("author"),
                    "page_number": chunk.get("page_number"),
                    "chapter": chunk.get("chapter"),
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
    
    def delete_book_vectors(self, filename: str):
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
                            match=MatchValue(value="book")
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"    Error deleting vectors for {filename}: {e}")

    def ingest_book(self, pdf_path: str):
        """Full pipeline: extract, embed, upload a single book."""
        # First, ensure idempotency by deleting any existing vectors for this file
        filename = os.path.basename(pdf_path)
        self.delete_book_vectors(filename)

        chunks = self.extract_text_from_pdf(pdf_path)
        
        if not chunks:
            print(f"  No chunks extracted from {pdf_path}")
            return 0
        
        embeddings = self.generate_embeddings(chunks)
        self.upload_to_qdrant(chunks, embeddings)
        
        return len(chunks)
    
    def ingest_all_books(self, books_dir: str) -> Dict[str, int]:
        """Ingest all PDF books from a directory."""
        results = {}
        
        if not os.path.exists(books_dir):
            print(f"Books directory not found: {books_dir}")
            return results
        
        pdf_files = [f for f in os.listdir(books_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {books_dir}")
            return results
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(books_dir, pdf_file)
            chunk_count = self.ingest_book(pdf_path)
            results[pdf_file] = chunk_count
        
        return results


if __name__ == "__main__":
    # Direct execution for testing
    ingester = BookIngester()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    books_dir = os.path.join(project_root, settings.RESOURCES_BOOKS_PATH)
    results = ingester.ingest_all_books(books_dir)
    
    print("\n=== Ingestion Complete ===")
    for file, count in results.items():
        print(f"  {file}: {count} chunks")
