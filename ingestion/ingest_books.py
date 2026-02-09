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
        Extract text from PDF and chunk based purely on word count.
        Collects all text first, then chunks based on CHUNK_SIZE setting.
        Page numbers are tracked for metadata but don't affect chunk boundaries.
        """
        metadata = self.extract_metadata_from_filename(os.path.basename(pdf_path))
        metadata["source_file"] = os.path.basename(pdf_path)  # Add source_file for Qdrant storage
        
        print(f"  Processing: {metadata['book_title']} by {metadata['author']}")
        
        # First pass: collect all text with page info
        page_texts = []  # List of (page_num, text, chapter)
        current_chapter = "Introduction"
        
        try:
            doc = fitz.open(pdf_path)
            total_words = 0
            
            for page_num, page in enumerate(doc, start=1):
                # Use blocks to filter headers and footers
                # blocks: (x0, y0, x1, y1, text, block_no, block_type)
                blocks = page.get_text("blocks")
                page_height = page.rect.height
                
                # Sort blocks by vertical position (top to bottom)
                blocks.sort(key=lambda b: b[1])
                
                valid_text_blocks = []
                full_page_text_for_detection = ""
                
                for b in blocks:
                    x0, y0, x1, y1, text, block_no, block_type = b
                    
                    # Skip non-text blocks (images, etc - block_type 0 is text)
                    if block_type != 0:
                        continue
                        
                    full_page_text_for_detection += text + "\n"
                    
                    # Filter logic:
                    # Headers: usually top 50-60px
                    # Footers: usually bottom 50px
                    if y1 < 60:  # Header threshold
                        continue
                    if y0 > page_height - 60:  # Footer threshold
                        continue
                        
                    valid_text_blocks.append(text)
                
                # Detect chapter from full text (including headers) to capture chapter titles that might be in headers
                detected_chapter = self.detect_chapter(full_page_text_for_detection, page_num)
                if detected_chapter:
                    current_chapter = detected_chapter
                
                # Join valid blocks with space to form page text
                # clean up whitespace
                cleaned_blocks = [blk.strip() for blk in valid_text_blocks if blk.strip()]
                page_text = ' '.join(cleaned_blocks)
                
                if not page_text:
                    continue
                
                page_texts.append((page_num, page_text, current_chapter))
                total_words += len(page_text.split())
            
            doc.close()
            print(f"    Total words extracted: {total_words}")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  Error processing {pdf_path}: {e}")
            print(tb)
            raise Exception(f"{e}\n{tb}")
        
        # Second pass: chunk based purely on word count
        all_chunks = self._chunk_document_by_words(page_texts, metadata)
        print(f"    Created {len(all_chunks)} chunks (target: ~{settings.CHUNK_SIZE} words each)")
        
        return all_chunks
    
    def _chunk_document_by_words(self, page_texts: List[tuple], metadata: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Chunk the entire document based on word count, ignoring page boundaries.
        Tracks page numbers for metadata but chunks flow across pages.
        """
        all_chunks = []
        
        # Combine all text into sentences with page tracking
        # Combine all text into sentences with page tracking
        all_sentences = []  # List of (sentence, page_num, chapter)
        
        # Pre-process: Join all page texts into one giant string to handle cross-page sentences
        # We need to map back to page numbers, so we'll keep track of character offsets?
        # Simpler approach: Join pages with space, but keep track of where pages start
        
        # Actually, let's keep the page-based iteration but handle the boundary carefully.
        # If we just join everything with spaces, we solve the "sentence split across pages" issue.
        
        combined_text = ""
        page_map = []  # List of (char_start, char_end, page_num, chapter)
        
        current_pos = 0
        for page_num, text, chapter in page_texts:
            # Add space between pages
            if combined_text:
                combined_text += " "
                current_pos += 1
            
            start = current_pos
            combined_text += text
            end = current_pos + len(text)
            page_map.append((start, end, page_num, chapter))
            current_pos = end
            
        # Split into sentences using regex
        # This handles the case where a sentence ends on page N and starts on page N+1
        # giving us a coherent sentence.
        sentences = re.split(r'(?<=[.!?])\s+', combined_text)
        
        current_sentence_start = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Find which page this sentence belongs to (mostly)
            # We'll attribute it to the page where the sentence starts
            # Approximate start position of this sentence in combined_text
            # Note: re.split consumes delimiters/whitespace, so exact mapping is tricky.
            # We'll find the first occurrence of this sentence starting from current search pos.
            
            found_start = combined_text.find(sentence, current_sentence_start)
            if found_start == -1:
                # Fallback, just increment
                found_start = current_sentence_start
            
            # Find page for found_start
            sent_page = 1
            sent_chapter = "Introduction"
            
            for p_start, p_end, p_num, p_chap in page_map:
                if p_start <= found_start < p_end:
                    sent_page = p_num
                    sent_chapter = p_chap
                    break
            
            all_sentences.append((sentence, sent_page, sent_chapter))
            current_sentence_start = found_start + len(sentence)
        
        # Now chunk based purely on word count
        current_chunk_sentences = []
        current_word_count = 0
        chunk_start_page = 1
        chunk_chapter = "Introduction"
        
        for sentence, page_num, chapter in all_sentences:
            sentence_words = len(sentence.split())
            
            # If adding this sentence exceeds chunk size, finalize current chunk
            if current_word_count + sentence_words > settings.CHUNK_SIZE and current_chunk_sentences:
                chunk_text = ' '.join(current_chunk_sentences)
                if len(chunk_text.strip()) > 50:  # Minimum chunk size
                    all_chunks.append({
                        "text": chunk_text,
                        "page_number": chunk_start_page,
                        "chapter": chunk_chapter,
                        "resource_type": "book",
                        "book_title": metadata["book_title"],
                        "author": metadata["author"],
                        "exact_text": chunk_text,
                        "source_file": metadata.get("source_file", "")
                    })
                
                # Keep overlap for context continuity
                overlap_sentences = []
                overlap_count = 0
                for s in reversed(current_chunk_sentences):
                    s_words = len(s.split())
                    if overlap_count + s_words <= settings.CHUNK_OVERLAP:
                        overlap_sentences.insert(0, s)
                        overlap_count += s_words
                    else:
                        break
                
                current_chunk_sentences = overlap_sentences
                current_word_count = overlap_count
                chunk_start_page = page_num
                chunk_chapter = chapter
            
            current_chunk_sentences.append(sentence)
            current_word_count += sentence_words
            
            # Update chapter if not set yet for this chunk
            if not chunk_chapter or chunk_chapter == "Introduction":
                chunk_chapter = chapter
        
        # Don't forget the last chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            if len(chunk_text.strip()) > 50:
                all_chunks.append({
                    "text": chunk_text,
                    "page_number": chunk_start_page,
                    "chapter": chunk_chapter,
                    "resource_type": "book",
                    "book_title": metadata["book_title"],
                    "author": metadata["author"],
                    "exact_text": chunk_text,
                    "source_file": metadata.get("source_file", "")
                })
        
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
