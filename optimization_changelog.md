# Performance Optimization Changelog
# Created: 2026-02-18
# Purpose: Log every change made so we can revert if needed (including .gitignore'd files)

---

## Change 1: Model Switch (settings.py + .env + schemas.py + claude_client.py)

### config/settings.py (line 16)
**ORIGINAL:**
```python
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
```
**CHANGED TO:**
```python
CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
```

### .env (line 6)
**ORIGINAL:**
```
CLAUDE_MODEL=claude-sonnet-4-20250514
```
**CHANGED TO:**
```
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### backend/schemas.py (line 60) — ROOT CAUSE: Frontend model override
**ORIGINAL:**
```python
model: Optional[str] = Field("claude-sonnet-4-5", description="Model ID to use (claude-haiku-4-5 or claude-sonnet-4-5)")
```
**CHANGED TO:**
```python
model: Optional[str] = Field(None, description="Model ID override (uses server default if not specified)")
```

### backend/claude_client.py (lines 111-112) — ROOT CAUSE: Model parameter override
**ORIGINAL:**
```python
            # Determine model to use
            target_model = model if model else self.model
```
**CHANGED TO:**
```python
            # Always use the server-configured model from settings
            # (frontend may send alias strings that don't reflect our config)
            target_model = self.model
```

---

## Change 2: Reduce max_tokens (claude_client.py)

### backend/claude_client.py (line 117)
**ORIGINAL:**
```python
max_tokens=4096,
```
**CHANGED TO:**
```python
max_tokens=2048,
```

---

## Change 3: Reduce Query Expansion (query_processor.py)

### backend/query_processor.py — expand_query method (lines 48-87)
**ORIGINAL (full method):**
```python
def expand_query(self, query: str) -> List[str]:
    queries = set()
    queries.add(query)
    
    # 1. Add synonym-expanded versions
    expanded = self._expand_with_synonyms(query)
    queries.add(expanded)
    
    # 2. Extract key concepts
    concepts = self._extract_key_concepts(query)
    if concepts:
        queries.add(concepts)
    
    # 3. Reformulate as different question types
    reformulations = self._reformulate_query(query)
    queries.update(reformulations)
    
    # 4. Add decomposed sub-queries if complex
    sub_queries = self._decompose_complex_query(query)
    queries.update(sub_queries)
    
    # 5. Add Case Study / Real World Scenarios variations (CRITICAL for evidence)
    queries.add(f"{query} case study")
    queries.add(f"{query} real world example")
    queries.add(f"{query} how they did it")
    
    # Remove empty strings and duplicates
    result = [q.strip() for q in queries if q.strip()]
    
    # Limit to 8 queries max for performance (increased for case studies)
    return list(set(result))[:8]
```
**CHANGED TO:**
```python
def expand_query(self, query: str) -> List[str]:
    queries = set()
    queries.add(query)
    
    # 1. Add synonym-expanded versions
    expanded = self._expand_with_synonyms(query)
    queries.add(expanded)
    
    # 2. Extract key concepts
    concepts = self._extract_key_concepts(query)
    if concepts:
        queries.add(concepts)
    
    # Remove empty strings and duplicates
    result = [q.strip() for q in queries if q.strip()]
    
    # Limit to 3 queries max for performance (reranker handles relevance)
    return list(set(result))[:3]
```

---

## Change 4: Batch Embed Queries (cohere_utils.py + vector_search.py)

### backend/cohere_utils.py
**ADDED new method `embed_queries`:**
```python
def embed_queries(self, queries: List[str], max_retries: int = 3, initial_wait: float = 10.0) -> List[List[float]]:
    """Batch embed multiple queries in a single API call."""
    embeddings = self._embed_batch_with_retry(
        queries,
        input_type="search_query",
        max_retries=max_retries,
        initial_wait=initial_wait
    )
    return embeddings
```

### backend/vector_search.py — search method (lines 200-278)
**ORIGINAL search flow:**
- Called `_single_query_search()` per query variation (which calls `embed_query()` individually)
- `fetch_limit = top_k * 3`

**CHANGED TO:**
- Batch embed all queries in one call
- Added `_search_with_embedding()` that takes pre-computed embedding
- `fetch_limit = top_k * 2`

### backend/vector_search.py — _rerank_with_cohere (line 148)
**ORIGINAL:**
```python
top_n=min(top_k * 2, len(documents))
```
**CHANGED TO:**
```python
top_n=min(top_k, len(documents))
```

---

## Change 5: Compress Evidence Context (claude_client.py)

### backend/claude_client.py — format_evidence_context method (lines 28-70)
**ORIGINAL (full method):**
```python
def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
    
    chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
    
    context_parts = ["=== EVIDENCE FROM RESOURCE LIBRARY ===\n"]
    
    for i, chunk in enumerate(chunks, 1):
        resource_type = chunk.get("resource_type", "unknown")
        text = chunk.get("exact_text", "")
        score = chunk.get("score", 0)
        
        if resource_type == "book":
            source_info = f"""
--- Evidence #{i} (Relevance: {score:.2f}) ---
Type: Book
Title: {chunk.get('book_title', 'Unknown')}
Author: {chunk.get('author', 'Unknown')}
Chapter: {chunk.get('chapter', 'Unknown')}
Page: {chunk.get('page_number', 'Unknown')}

Content:
\"\"\"{text}\"\"\"
"""
        else:  # article
            source_info = f"""
--- Evidence #{i} (Relevance: {score:.2f}) ---
Type: Article
Title: {chunk.get('article_title', 'Unknown')}
Authors: {chunk.get('authors', 'Unknown')}
Section: {chunk.get('section_heading', 'Unknown')}
URL: {chunk.get('url', 'N/A')}

Content:
\"\"\"{text}\"\"\"
"""
        context_parts.append(source_info)
    
    context_parts.append("\n=== END OF EVIDENCE ===")
    return "\n".join(context_parts)
```
**CHANGED TO:** (compact single-line source format, no scores)
```python
def format_evidence_context(self, chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "NO EVIDENCE AVAILABLE - Must respond with 'No sufficient evidence found in the current resource library.'"
    
    chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
    
    context_parts = ["EVIDENCE:\n"]
    
    for i, chunk in enumerate(chunks, 1):
        resource_type = chunk.get("resource_type", "unknown")
        text = chunk.get("exact_text", "")
        
        if resource_type == "book":
            source = f"Book: {chunk.get('book_title', 'Unknown')}, {chunk.get('author', 'Unknown')}, Ch.{chunk.get('chapter', '?')}, P.{chunk.get('page_number', '?')}"
        else:
            source = f"Article: {chunk.get('article_title', 'Unknown')}, Section: {chunk.get('section_heading', '?')}"
            if chunk.get('url'):
                source += f", URL: {chunk.get('url')}"
        
        context_parts.append(f"[{i}] {source}\n\"\"\"{text}\"\"\"\n")
    
    return "\n".join(context_parts)
```

---

## HOW TO REVERT ALL CHANGES

To fully revert, restore each "ORIGINAL" block listed above into the corresponding file and line.
The most critical ones to revert are:
1. `.env` — CLAUDE_MODEL back to `claude-sonnet-4-20250514`
2. `config/settings.py` — CLAUDE_MODEL default back to `claude-sonnet-4-20250514`
3. `backend/claude_client.py` — max_tokens back to `4096`, format_evidence_context back to verbose
4. `backend/query_processor.py` — expand_query back to full 8-query version
5. `backend/vector_search.py` — revert search to per-query embedding, fetch_limit back to `top_k * 3`, rerank top_n back to `top_k * 2`
6. `backend/cohere_utils.py` — remove the `embed_queries` method (optional, doesn't hurt)
