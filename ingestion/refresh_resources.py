"""
Resource Refresh Module
Idempotent ingestion of new PDFs only.
Tracks processed files to avoid re-processing.
"""

import os
import json
import hashlib
from typing import Set, Dict, Any
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from ingestion.ingest_books import BookIngester
from ingestion.ingest_html_articles import HTMLArticleIngester
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


class ResourceRefresher:
    """Handles incremental refresh of resources."""
    
    def __init__(self, project_root: str = None):
        """Initialize the refresher."""
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.project_root = project_root
        self.processed_files_path = os.path.join(project_root, settings.PROCESSED_FILES_PATH)
        
        # Debug logging
        print(f"\n=== ResourceRefresher Init ===")
        print(f"  project_root: {self.project_root}")
        print(f"  processed_files_path: {self.processed_files_path}")
        print(f"  Path exists: {os.path.exists(self.processed_files_path)}")
        
        self.processed_files = self._load_processed_files()
        print(f"  Loaded processed_files: {list(self.processed_files.keys())}")
    
    def _load_processed_files(self) -> Dict[str, str]:
        """Load the set of already processed files with their hashes."""
        if os.path.exists(self.processed_files_path):
            try:
                with open(self.processed_files_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load processed files: {e}")
        return {}
    
    def _save_processed_files(self):
        """Save the set of processed files."""
        try:
            with open(self.processed_files_path, 'w') as f:
                json.dump(self.processed_files, f, indent=2)
        except Exception as e:
            print(f"Error saving processed files: {e}")
    
    def _get_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file for change detection."""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error hashing file {filepath}: {e}")
            return ""
    
    def _prune_missing_files(self, active_files: Set[str]):
        """
        Delete vectors for files that are in Qdrant but not in the active file list.
        Also remove entries from processed_files for files that no longer exist on disk.
        """
        print("\n=== Checking for deleted files ===")
        
        # Step 1: Clean up processed_files for files that no longer exist on disk
        # This ensures re-added files are detected as "new"
        keys_to_remove = []
        for key in self.processed_files:
            # Key format: "book:filename.pdf" or "article:filename.pdf"
            parts = key.split(":", 1)
            if len(parts) == 2:
                filename = parts[1]
                if filename not in active_files:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            print(f"  Removing stale entry from processed_files: {key}")
            del self.processed_files[key]
        try:
            client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            
            # Get all source files currently in DB
            # Note: This scroll approach is simple but fine for this scale
            source_files_in_db = set()
            offset = None
            
            while True:
                scroll_result = client.scroll(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    scroll_filter=None,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset
                )
                
                points, next_offset = scroll_result
                if not points:
                    break
                    
                for point in points:
                    sf = point.payload.get("source_file")
                    if sf:
                        source_files_in_db.add(sf)
                
                offset = next_offset
                if offset is None:
                    break
            
            # Identify files to delete
            files_to_delete = source_files_in_db - active_files
            
            if not files_to_delete:
                print("  No files to prune.")
                return 0
                
            print(f"  Found {len(files_to_delete)} files to delete: {files_to_delete}")
            
            for filename in files_to_delete:
                print(f"  Pruning: {filename}")
                client.delete(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="source_file",
                                match=MatchValue(value=filename)
                            )
                        ]
                    )
                )
                
                # Also remove from processed_files.json if present
                keys_to_remove = [k for k in self.processed_files if k.endswith(f":{filename}")]
                for k in keys_to_remove:
                    del self.processed_files[k]
                    
            return len(files_to_delete)
            
        except Exception as e:
            print(f"  Error during pruning: {e}")
            return 0

    def _get_new_files(self, directory: str, resource_type: str, force: bool = False, extensions: list = None) -> list:
        """Get list of new or modified files in directory."""
        if extensions is None:
            extensions = ['.pdf']
        new_files = []
        
        if not os.path.exists(directory):
            print(f"Directory not found: {directory}")
            return new_files
        
        for filename in os.listdir(directory):
            if not any(filename.lower().endswith(ext) for ext in extensions):
                continue
            
            filepath = os.path.normpath(os.path.join(directory, filename))
            file_key = f"{resource_type}:{filename}"
            file_hash = self._get_file_hash(filepath)
            
            # If force is True, we add it regardless of processed state
            if force:
                new_files.append((filepath, file_key, file_hash))
                print(f"  [FORCE] Re-processing file: {filename}")
            elif file_key not in self.processed_files:
                new_files.append((filepath, file_key, file_hash))
                print(f"  New file detected: {filename}")
            elif self.processed_files[file_key] != file_hash:
                new_files.append((filepath, file_key, file_hash))
                print(f"  Modified file detected: {filename}")
        
        return new_files
    
    def refresh(self, force: bool = False) -> Dict[str, Any]:
        """
        Scan resource folders and ingest new/modified PDFs.
        If force=True, re-ingest ALL PDFs.
        
        Returns:
            Dict with counts of processed files by type
        """
        results = {
            "books_processed": 0,
            "books_chunks": 0,
            "articles_processed": 0,
            "articles_chunks": 0,
            "errors": []
        }
        
        books_dir = os.path.join(self.project_root, settings.RESOURCES_BOOKS_PATH)
        articles_dir = os.path.join(self.project_root, settings.RESOURCES_ARTICLES_PATH)
        
        # Check for new books
        print(f"\n=== Scanning for {'ALL' if force else 'new'} books ===")
        new_books = self._get_new_files(books_dir, "book", force=force)
        
        if new_books:
            book_ingester = BookIngester()
            for filepath, file_key, file_hash in new_books:
                try:
                    chunk_count = book_ingester.ingest_book(filepath)
                    self.processed_files[file_key] = file_hash
                    results["books_processed"] += 1
                    results["books_chunks"] += chunk_count
                except Exception as e:
                    error_msg = f"Error processing {filepath}: {e}"
                    print(error_msg)
                    results["errors"].append(error_msg)
        else:
            print("  No books to process")
        
        # Check for new HTML articles
        print(f"\n=== Scanning for {'ALL' if force else 'new'} HTML articles ===")
        new_html_articles = self._get_new_files(articles_dir, "html_article", force=force, extensions=['.html', '.htm'])
        
        if new_html_articles:
            html_ingester = HTMLArticleIngester()
            for filepath, file_key, file_hash in new_html_articles:
                try:
                    chunk_count = html_ingester.ingest_article(filepath)
                    self.processed_files[file_key] = file_hash
                    results["articles_processed"] += 1
                    results["articles_chunks"] += chunk_count
                except Exception as e:
                    error_msg = f"Error processing {filepath}: {e}"
                    print(error_msg)
                    results["errors"].append(error_msg)
        else:
            print("  No HTML articles to process")
        
        # Collect all currently active files for pruning
        active_files = set()
        if os.path.exists(books_dir):
            active_files.update([f for f in os.listdir(books_dir) if f.lower().endswith('.pdf')])
        if os.path.exists(articles_dir):
            active_files.update([f for f in os.listdir(articles_dir) if f.lower().endswith(('.html', '.htm'))])
            
        pruned_count = self._prune_missing_files(active_files)
        
        # Save updated processed files list (AFTER pruning!)
        self._save_processed_files()
        
        print("\n=== Refresh Complete ===")
        print(f"  Books: {results['books_processed']} files, {results['books_chunks']} chunks")
        print(f"  Articles: {results['articles_processed']} files, {results['articles_chunks']} chunks")
        print(f"  Pruned: {pruned_count} deleted files")
        if results["errors"]:
            print(f"  Errors: {len(results['errors'])}")
        
        return results


def refresh_resources(project_root: str = None, force: bool = False) -> Dict[str, Any]:
    """Convenience function to run refresh."""
    refresher = ResourceRefresher(project_root)
    return refresher.refresh(force=force)


if __name__ == "__main__":
    # Direct execution
    results = refresh_resources()
    print(f"\nFinal results: {results}")
