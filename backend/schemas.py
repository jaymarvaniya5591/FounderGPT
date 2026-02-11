"""
Pydantic Schemas for FounderGPT API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level for citations."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Citation(BaseModel):
    """A single citation with source and confidence."""
    exact_quote: str
    resource_type: str  # "book" or "article"
    
    # Book fields
    book_title: Optional[str] = None
    author: Optional[str] = None
    page_number: Optional[int] = None
    chapter: Optional[str] = None
    
    # Article fields
    article_title: Optional[str] = None
    authors: Optional[str] = None
    url: Optional[str] = None
    section_heading: Optional[str] = None
    
    confidence: ConfidenceLevel


class ChunkMetadata(BaseModel):
    """Metadata for a retrieved chunk."""
    resource_type: str
    exact_text: str
    score: float
    
    # Book fields
    book_title: Optional[str] = None
    author: Optional[str] = None
    page_number: Optional[int] = None
    chapter: Optional[str] = None
    
    # Article fields
    article_title: Optional[str] = None
    authors: Optional[str] = None
    url: Optional[str] = None
    section_heading: Optional[str] = None


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""
    query: str = Field(..., min_length=1, description="The founder's messy input")
    category_id: str = Field(..., description="Selected category ID (idea-validation, marketing-growth, other)")
    model: Optional[str] = Field("claude-sonnet-4-5", description="Model ID to use (claude-haiku-4-5 or claude-sonnet-4-5)")


class StructuredSection(BaseModel):
    """A section of the structured response."""
    content: str
    citations: List[Citation] = []


class AskResponse(BaseModel):
    """Response body for /ask endpoint."""
    success: bool
    
    # The five required sections
    section_a_problem: Optional[str] = None
    section_b_agreement: Optional[str] = None
    section_c_disagreement: Optional[str] = None
    section_d_action: Optional[str] = None
    section_e_avoid: Optional[str] = None
    
    # Full formatted response
    full_response: Optional[str] = None
    
    # Metadata
    chunks_retrieved: int = 0
    error: Optional[str] = None
    
    # LLM Provider that generated the response (OpenAI, Claude, or Gemini)
    llm_provider: Optional[str] = None

    # Timing Data
    timing_data: Optional[Dict[str, float]] = None


class RefreshRequest(BaseModel):
    """Request body for /refresh endpoint (optional)."""
    force: bool = False  # Force re-process all files


class RefreshResponse(BaseModel):
    """Response body for /refresh endpoint."""
    success: bool
    books_processed: int = 0
    books_chunks: int = 0
    articles_processed: int = 0
    articles_chunks: int = 0
    errors: List[str] = []
    message: str = ""


# Category Management Schemas
class CategoryCreate(BaseModel):
    """Request body for creating a category."""
    name: str = Field(..., min_length=1, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    admin_password: str = Field(..., description="Admin password for authentication")


class CategoryResponse(BaseModel):
    """Response body for a single category."""
    id: str
    name: str
    description: Optional[str] = None


class CategoriesListResponse(BaseModel):
    """Response body for listing categories."""
    success: bool
    categories: List[CategoryResponse] = []
    error: Optional[str] = None


class CategoryDeleteRequest(BaseModel):
    """Request body for deleting a category."""
    admin_password: str = Field(..., description="Admin password for authentication")


# Resource Management Schemas
class ResourceResponse(BaseModel):
    """Response body for a single resource."""
    source_file: str
    title: str
    author: str
    resource_type: str
    url: Optional[str] = None
    chunk_count: int = 0


class ResourcesListResponse(BaseModel):
    """Response body for listing resources."""
    success: bool
    resources: List[ResourceResponse] = []
    error: Optional[str] = None


class ResourceDeleteRequest(BaseModel):
    """Request body for deleting a resource."""
    resource_type: str = Field(..., description="'book' or 'article'")
    admin_password: str = Field(..., description="Admin password for authentication")


class ArticleLinkResponse(BaseModel):
    """Response body for getting an article's link."""
    success: bool
    source_file: str
    url: Optional[str] = None
    error: Optional[str] = None


class AdminVerifyRequest(BaseModel):
    """Request body for verifying admin password."""
    admin_password: str = Field(..., description="Admin password to verify")


class AdminVerifyResponse(BaseModel):
    """Response body for admin verification."""
    success: bool
    message: str = ""

