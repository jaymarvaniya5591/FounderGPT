"""
Resource Management Module
Handles listing and deletion of books and articles from Qdrant.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings


@dataclass
class Resource:
    """Represents a book or article resource."""
    source_file: str
    title: str
    author: str
    resource_type: str  # "book" or "article"
    url: Optional[str] = None
    chunk_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResourceManager:
    """Manages resource listing and deletion from Qdrant."""
    
    _instance = None
    _qdrant_client = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Qdrant client."""
        if ResourceManager._qdrant_client is None:
            ResourceManager._qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
    
    @property
    def qdrant(self):
        return ResourceManager._qdrant_client
    
    def list_resources(
        self,
        resource_type: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> List[Resource]:
        """
        List all unique resources (books/articles) from Qdrant.
        Optionally filter by resource_type ('book' or 'article').
        """
        resources_map = {}  # source_file -> Resource
        
        # Build filter conditions
        filter_conditions = []
        if resource_type:
            filter_conditions.append(
                FieldCondition(key="resource_type", match=MatchValue(value=resource_type))
            )
        if category_id:
            filter_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category_id))
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Scroll through all points
        offset = None
        while True:
            try:
                scroll_result = self.qdrant.scroll(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    scroll_filter=search_filter,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset
                )
                
                points, next_offset = scroll_result
                if not points:
                    break
                
                for point in points:
                    payload = point.payload
                    source_file = payload.get("source_file")
                    
                    if source_file and source_file not in resources_map:
                        res_type = payload.get("resource_type", "book")
                        
                        if res_type == "book":
                            title = payload.get("book_title", source_file)
                            author = payload.get("author", "Unknown")
                        else:
                            title = payload.get("article_title", source_file)
                            author = payload.get("authors", "Unknown")
                        
                        resources_map[source_file] = Resource(
                            source_file=source_file,
                            title=title,
                            author=author,
                            resource_type=res_type,
                            url=payload.get("url"),
                            chunk_count=1
                        )
                    elif source_file:
                        resources_map[source_file].chunk_count += 1
                
                offset = next_offset
                if offset is None:
                    break
                    
            except Exception as e:
                print(f"Error scrolling Qdrant: {e}")
                break
        
        return list(resources_map.values())
    
    def get_resource(self, source_file: str) -> Optional[Resource]:
        """Get a single resource by source file name."""
        resources = self.list_resources()
        for res in resources:
            if res.source_file == source_file:
                return res
        return None
    
    def delete_resource(self, source_file: str, resource_type: str) -> bool:
        """
        Delete all vectors associated with a resource.
        Returns True if deletion was successful.
        """
        try:
            self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file)
                        ),
                        FieldCondition(
                            key="resource_type",
                            match=MatchValue(value=resource_type)
                        )
                    ]
                )
            )
            print(f"Deleted vectors for {source_file}")
            return True
        except Exception as e:
            print(f"Error deleting resource {source_file}: {e}")
            return False
    
    def get_article_link(self, source_file: str) -> Optional[str]:
        """
        Get the URL for an article resource.
        Returns None if not found or not an article.
        """
        try:
            # Search for any point with this source file
            scroll_result = self.qdrant.scroll(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file)
                        ),
                        FieldCondition(
                            key="resource_type",
                            match=MatchValue(value="article")
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            points, _ = scroll_result
            if points:
                return points[0].payload.get("url")
            return None
            
        except Exception as e:
            print(f"Error getting article link: {e}")
            return None
    
    def get_resource_count(self) -> Dict[str, int]:
        """Get count of books and articles."""
        resources = self.list_resources()
        counts = {"books": 0, "articles": 0, "total_chunks": 0}
        
        for res in resources:
            if res.resource_type == "book":
                counts["books"] += 1
            else:
                counts["articles"] += 1
            counts["total_chunks"] += res.chunk_count
        
        return counts


# Global instance
resource_manager = ResourceManager()
