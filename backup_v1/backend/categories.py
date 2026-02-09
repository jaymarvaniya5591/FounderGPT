"""
Category Management Module
Handles CRUD operations for resource categories.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Category:
    """Represents a resource category."""
    id: str
    name: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CategoryManager:
    """Manages category CRUD operations with JSON file storage."""
    
    def __init__(self, categories_file: str = None):
        """Initialize category manager with storage file path."""
        if categories_file is None:
            # Default to config/categories.json relative to project root
            project_root = Path(__file__).parent.parent
            categories_file = project_root / "config" / "categories.json"
        
        self.categories_file = Path(categories_file)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create categories file with default data if it doesn't exist."""
        if not self.categories_file.exists():
            self.categories_file.parent.mkdir(parents=True, exist_ok=True)
            default_data = {
                "categories": [
                    {
                        "id": "idea-validation",
                        "name": "Idea Validation and Customer Discovery",
                        "description": "Understanding customer problems, validating ideas, and discovering market fit"
                    }
                ]
            }
            self._save_data(default_data)
    
    def _load_data(self) -> Dict[str, Any]:
        """Load categories from JSON file."""
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"categories": []}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save categories to JSON file."""
        with open(self.categories_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def list_categories(self) -> List[Category]:
        """Get all categories."""
        data = self._load_data()
        return [
            Category(
                id=cat["id"],
                name=cat["name"],
                description=cat.get("description")
            )
            for cat in data.get("categories", [])
        ]
    
    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a single category by ID."""
        categories = self.list_categories()
        for cat in categories:
            if cat.id == category_id:
                return cat
        return None
    
    def add_category(self, name: str, description: Optional[str] = None) -> Category:
        """Add a new category."""
        data = self._load_data()
        
        # Generate URL-friendly ID from name
        category_id = name.lower().replace(" ", "-").replace("&", "and")
        category_id = ''.join(c for c in category_id if c.isalnum() or c == '-')
        
        # Ensure uniqueness
        existing_ids = {cat["id"] for cat in data.get("categories", [])}
        if category_id in existing_ids:
            category_id = f"{category_id}-{uuid.uuid4().hex[:6]}"
        
        new_category = Category(
            id=category_id,
            name=name,
            description=description
        )
        
        data["categories"].append(new_category.to_dict())
        self._save_data(data)
        
        return new_category
    
    def delete_category(self, category_id: str) -> bool:
        """Delete a category by ID. Returns True if deleted, False if not found."""
        data = self._load_data()
        original_count = len(data.get("categories", []))
        
        data["categories"] = [
            cat for cat in data.get("categories", [])
            if cat["id"] != category_id
        ]
        
        if len(data["categories"]) < original_count:
            self._save_data(data)
            return True
        return False
    
    def update_category(self, category_id: str, name: str = None, description: str = None) -> Optional[Category]:
        """Update an existing category."""
        data = self._load_data()
        
        for cat in data.get("categories", []):
            if cat["id"] == category_id:
                if name is not None:
                    cat["name"] = name
                if description is not None:
                    cat["description"] = description
                self._save_data(data)
                return Category(
                    id=cat["id"],
                    name=cat["name"],
                    description=cat.get("description")
                )
        
        return None


# Global instance
category_manager = CategoryManager()
