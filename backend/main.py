"""
FounderGPT Backend - FastAPI Application
Main entry point for the API server.
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode characters (em-dashes, etc.)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import AskRequest, AskResponse, RefreshResponse, RefreshRequest
from backend.vector_search import VectorSearch, search_resources
from backend.llm_gateway import LLMGateway, get_founder_advice
from config.settings import settings


# Initialize FastAPI app
app = FastAPI(
    title="FounderGPT",
    description="A platform for founders under stress. Convert chaos into clarity.",
    version="1.0.0"
)

# Add CORS middleware for production and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://scoutmate.in",
        "https://www.scoutmate.in",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # Allow all origins for now, can restrict later
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (lazy loading)
vector_search = None
llm_gateway = None


def get_vector_search():
    """Lazy initialization of vector search."""
    global vector_search
    if vector_search is None:
        vector_search = VectorSearch()
    return vector_search


def get_llm_gateway():
    """Lazy initialization of LLM gateway."""
    global llm_gateway
    if llm_gateway is None:
        llm_gateway = LLMGateway()
    return llm_gateway


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Main endpoint for founder questions.
    
    Takes messy, unstructured input and returns structured,
    evidence-backed advice following the strict 5-section format.
    """
    try:
        print(f"\n{'='*60}", flush=True)
        print(f"[ASK] Received query: {request.query[:100]}...", flush=True)
        print(f"{'='*60}", flush=True)
        
        # 1. Use User-Selected Category
        category_id = request.category_id
        print(f"[ASK] User selected category: {category_id}", flush=True)
        
        from backend.prompts import IDEA_VALIDATION_PROMPT, MARKETING_PROMPT, OTHER_CATEGORY_PROMPT, GENERAL_PROMPT

        # Select prompt based on category
        if category_id == "marketing-growth":
            system_prompt = MARKETING_PROMPT
            print(f"[ASK] Using MARKETING logic (up to 5 citations, diverse sources)", flush=True)
        elif category_id == "other":
            system_prompt = OTHER_CATEGORY_PROMPT
            print(f"[ASK] Using OTHER/STRICT logic (strict 1-3 citations)", flush=True)
        elif category_id == "idea-validation":
            system_prompt = IDEA_VALIDATION_PROMPT
            print(f"[ASK] Using VALIDATION logic (standard 3 citations)", flush=True)
        else:
            # Default to General Prompt for any new/unknown categories
            system_prompt = GENERAL_PROMPT
            print(f"[ASK] Using GENERAL logic (standard template)", flush=True)
        
        # Get vector search instance
        vs = get_vector_search()
        
        # Search for relevant chunks
        # Note: We could tune top_k based on intent (e.g., fetch more for marketing to get diversity)
        search_top_k = settings.TOP_K_RESULTS
        if category_id == "marketing-growth":
            search_top_k = 20  # Fetch more to allow for diversity selection
            
        chunks = vs.search(request.query, top_k=search_top_k)
        
        print(f"\n[ASK] Retrieved {len(chunks)} chunks", flush=True)
        
        # If no chunks found, return insufficient evidence response
        if not chunks:
            return AskResponse(
                success=True,
                full_response="No sufficient evidence found in the current resource library.\n\nPlease add relevant books or articles to the resources folder and refresh the database.",
                chunks_retrieved=0
            )
        
        # Get LLM gateway and generate response
        gateway = get_llm_gateway()
        result = gateway.generate_response(request.query, chunks, system_prompt=system_prompt)
        
        if not result["success"]:
            return AskResponse(
                success=False,
                error=result.get("error", "Unknown error occurred"),
                chunks_retrieved=len(chunks)
            )
        
        # Parse sections from result
        sections = result.get("sections", {})
        
        return AskResponse(
            success=True,
            section_a_problem=sections.get("section_a"),
            section_b_agreement=sections.get("section_b"),
            section_c_disagreement=sections.get("section_c"),
            section_d_action=sections.get("section_d"),
            section_e_avoid=sections.get("section_e"),
            full_response=result.get("full_response"),
            chunks_retrieved=len(chunks),
            llm_provider=result.get("llm_provider")
        )
        
    except Exception as e:
        return AskResponse(
            success=False,
            error=str(e),
            chunks_retrieved=0
        )


@app.post("/refresh", response_model=RefreshResponse)
async def refresh_database(request: RefreshRequest = None):
    """
    Refresh the vector database with new resources.
    
    Optional 'force' parameter in body triggers a full re-scan.
    NOTE: This endpoint only works in local development where PyMuPDF is installed.
    """
    try:
        # Check if PyMuPDF (fitz) is available - it's not installed in production
        try:
            import fitz  # noqa: F401
        except ImportError:
            return RefreshResponse(
                success=False,
                errors=["PyMuPDF not installed"],
                message="Refresh is only available in local development. Please run refresh locally and push to deploy."
            )
        
        # Import here to avoid circular imports
        from ingestion.refresh_resources import refresh_resources
        
        # Default to False if no body
        force = request.force if request else False
        
        # Run refresh
        results = refresh_resources(str(project_root), force=force)
        
        return RefreshResponse(
            success=True,
            books_processed=results.get("books_processed", 0),
            books_chunks=results.get("books_chunks", 0),
            articles_processed=results.get("articles_processed", 0),
            articles_chunks=results.get("articles_chunks", 0),
            errors=results.get("errors", []),
            message=f"Processed {results.get('books_processed', 0)} books and {results.get('articles_processed', 0)} articles"
        )
        
    except Exception as e:
        return RefreshResponse(
            success=False,
            errors=[str(e)],
            message=f"Refresh failed: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get statistics about the vector database."""
    try:
        vs = get_vector_search()
        stats = vs.get_collection_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "FounderGPT"}


@app.get("/ping")
async def ping():
    """Keep-alive endpoint for Render free tier."""
    return {"status": "ok"}


@app.get("/cached-data")
async def get_cached_data():
    """
    Fast endpoint returning categories + resources from static index file.
    No Qdrant queries - reads from resources_index.json.
    """
    import json
    from datetime import datetime
    
    index_path = project_root / settings.RESOURCES_INDEX_FILE
    
    try:
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "success": True,
                "categories": data.get("categories", []),
                "books": data.get("books", []),
                "articles": data.get("articles", []),
                "last_updated": data.get("last_updated")
            }
        else:
            # Fallback: build from slow queries if index missing
            from backend.categories import category_manager
            from backend.resources import resource_manager
            
            categories = category_manager.list_categories()
            resources = resource_manager.list_resources()
            
            books = [r.to_dict() for r in resources if r.resource_type == "book"]
            articles = [r.to_dict() for r in resources if r.resource_type == "article"]
            
            return {
                "success": True,
                "categories": [{"id": c.id, "name": c.name, "description": c.description} for c in categories],
                "books": books,
                "articles": articles,
                "last_updated": datetime.now().isoformat()
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========================================
# Category Management Endpoints
# ========================================

from backend.categories import category_manager
from backend.resources import resource_manager
from backend.auth import verify_admin_password
from backend.schemas import (
    CategoryCreate, CategoryResponse, CategoriesListResponse, CategoryDeleteRequest,
    ResourceResponse, ResourcesListResponse, ResourceDeleteRequest, ArticleLinkResponse,
    AdminVerifyRequest, AdminVerifyResponse
)


@app.get("/categories", response_model=CategoriesListResponse)
async def list_categories():
    """Get all categories."""
    try:
        categories = category_manager.list_categories()
        return CategoriesListResponse(
            success=True,
            categories=[
                CategoryResponse(id=c.id, name=c.name, description=c.description)
                for c in categories
            ]
        )
    except Exception as e:
        return CategoriesListResponse(success=False, error=str(e))


@app.post("/categories", response_model=CategoryResponse)
async def create_category(request: CategoryCreate):
    """Create a new category. Requires admin password."""
    if not verify_admin_password(request.admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    try:
        category = category_manager.add_category(request.name, request.description)
        return CategoryResponse(id=category.id, name=category.name, description=category.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/categories/{category_id}")
async def delete_category(category_id: str, request: CategoryDeleteRequest):
    """Delete a category. Requires admin password."""
    if not verify_admin_password(request.admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    deleted = category_manager.delete_category(category_id)
    if deleted:
        return {"success": True, "message": f"Category '{category_id}' deleted"}
    else:
        raise HTTPException(status_code=404, detail="Category not found")


# ========================================
# Resource Management Endpoints
# ========================================

@app.get("/resources", response_model=ResourcesListResponse)
async def list_resources(resource_type: str = None):
    """List all resources. Optionally filter by 'book' or 'article'."""
    try:
        resources = resource_manager.list_resources(resource_type=resource_type)
        return ResourcesListResponse(
            success=True,
            resources=[
                ResourceResponse(
                    source_file=r.source_file,
                    title=r.title,
                    author=r.author,
                    resource_type=r.resource_type,
                    url=r.url,
                    chunk_count=r.chunk_count
                )
                for r in resources
            ]
        )
    except Exception as e:
        return ResourcesListResponse(success=False, error=str(e))


@app.get("/categories/{category_id}/resources", response_model=ResourcesListResponse)
async def list_category_resources(category_id: str, resource_type: str = None):
    """List resources by category. NOTE: Category filtering requires resources to have category metadata."""
    try:
        resources = resource_manager.list_resources(resource_type=resource_type, category_id=category_id)
        return ResourcesListResponse(
            success=True,
            resources=[
                ResourceResponse(
                    source_file=r.source_file,
                    title=r.title,
                    author=r.author,
                    resource_type=r.resource_type,
                    url=r.url,
                    chunk_count=r.chunk_count
                )
                for r in resources
            ]
        )
    except Exception as e:
        return ResourcesListResponse(success=False, error=str(e))


@app.delete("/resources/{source_file:path}")
async def delete_resource(source_file: str, request: ResourceDeleteRequest):
    """Delete a resource and all its vectors. Requires admin password."""
    if not verify_admin_password(request.admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    deleted = resource_manager.delete_resource(source_file, request.resource_type)
    if deleted:
        return {"success": True, "message": f"Resource '{source_file}' deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete resource")


@app.get("/resources/{source_file:path}/link", response_model=ArticleLinkResponse)
async def get_article_link(source_file: str):
    """Get the URL for an article resource."""
    url = resource_manager.get_article_link(source_file)
    return ArticleLinkResponse(
        success=True,
        source_file=source_file,
        url=url
    )


# ========================================
# Admin Verification Endpoint
# ========================================

@app.post("/verify-admin", response_model=AdminVerifyResponse)
async def verify_admin(request: AdminVerifyRequest):
    """Verify admin password without performing any action."""
    if verify_admin_password(request.admin_password):
        return AdminVerifyResponse(success=True, message="Admin verified")
    else:
        return AdminVerifyResponse(success=False, message="Invalid password")

# Serve static frontend files
frontend_dir = project_root / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return {"message": "FounderGPT API is running. Frontend not found."}


@app.get("/{file_path:path}")
async def serve_static_files(file_path: str):
    """
    Catch-all route to serve static files (CSS, JS, etc.) from frontend directory.
    This allows relative paths in HTML to work, matching Vercel's behavior.
    """
    # Skip API routes
    if file_path.startswith(("ask", "refresh", "stats", "health", "categories", "resources", "verify-admin", "static/")):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Try to serve the requested file from frontend directory
    file = frontend_dir / file_path
    if file.exists() and file.is_file():
        return FileResponse(str(file))
    
    # If file not found, return 404
    raise HTTPException(status_code=404, detail="File not found")


def kill_existing_listeners(port: int = 8000):
    """
    Kill any existing process listening on the specified port.
    """
    import subprocess
    import time
    
    print(f"\n🔍 Checking for existing listeners on port {port}...")
    
    try:
        # Find processes using netstat
        result = subprocess.run(
            f'netstat -ano | findstr :{port} | findstr LISTENING',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids_killed = set()
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and pid not in pids_killed and pid != '0':
                        try:
                            subprocess.run(
                                f'taskkill /F /PID {pid}',
                                shell=True,
                                capture_output=True,
                                text=True
                            )
                            print(f"   ✅ Killed process PID {pid}")
                            pids_killed.add(pid)
                        except Exception:
                            pass
            
            if pids_killed:
                print(f"   ⏳ Waiting for port to be released...")
                time.sleep(2)  # Wait 2 seconds for Windows to release
                print(f"   ✅ Port should now be available")
        else:
            print(f"   ✅ Port {port} is available")
            
    except Exception as e:
        print(f"   ⚠️ Could not check port: {e}")


if __name__ == "__main__":
    import uvicorn
    
    # Kill any existing listeners BEFORE starting server
    kill_existing_listeners(8000)
    
    print("\n" + "="*50)
    print("  FounderGPT Backend Server")
    print("="*50)
    print(f"\n  Starting server at http://localhost:8000")
    print(f"  API docs at http://localhost:8000/docs")
    print(f"\n  Press Ctrl+C to stop")
    print("="*50 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
