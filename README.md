# YourGuide

**Convert chaos into clarity.** An advisor for founders under stress.

YourGuide takes messy, unstructured founder input and returns structured, evidence-backed advice using only content from great business books and articles stored in a private vector database.

---

## Quick Start

### 1. Install Dependencies

```bash
cd c:\Users\marva\Documents\project-startupguru\antigravity-code
pip install -r requirements.txt
```

### 2. Set Qdrant API Key

Set the environment variable for your Qdrant Cloud API key:

```powershell
$env:QDRANT_API_KEY = "your-qdrant-api-key"
```

Or create a `.env` file in the project root:
```
QDRANT_API_KEY=your-qdrant-api-key
```

### 3. Add Resources (Optional but Recommended)

Place PDF files in the resource folders:
- **Books**: `resources/books/` (format: `Title - Author.pdf`)
- **Articles**: `resources/articles/` (format: `Title - Author.pdf`)

### 4. Run the Server

```bash
python backend/main.py
```

### 5. Open the Application

Navigate to: **http://localhost:8000**

---

## How It Works

### Input → Vector Search → Claude → Structured Response

```
[Messy Founder Input]
        ↓
[Embedding Model] → [Qdrant Search] → [Top 10 Relevant Chunks]
        ↓
[Claude Sonnet 4.5] ← [Strict System Prompt]
        ↓
[Structured 5-Section Response with Citations]
```

---

## Chunking Strategy

The system uses **semantic chunking**, not fixed-size splitting:

1. **Sentence Boundary Splitting**: Text is split at sentence endings (`.`, `!`, `?`)
2. **Target Size**: ~500 words per chunk with 50-word overlap
3. **Page Awareness**: Each chunk knows its source page number
4. **Chapter Detection**: Pattern matching for "Chapter X", "PART I", etc.
5. **Minimum Threshold**: Chunks under 50 characters are discarded

**Why semantic chunking?**
- Preserves context and meaning
- Avoids cutting sentences mid-thought
- Better retrieval quality than fixed-size splits

---

## Confidence Scoring Logic

Each cited resource is assigned a confidence level:

| Level | Definition | Indicators |
|-------|------------|------------|
| **High** | Multiple independent sources align OR author speaks from repeated real-world experience | Direct experience, case studies, consistent findings |
| **Medium** | Strong argument but context-dependent OR supported by limited examples | Single source, theoretical, "it depends" |
| **Low** | Anecdotal, controversial, or highly situation-specific | One-off stories, contested views, narrow context |

**Rules:**
- Confidence is assigned per resource, not per section
- Claude never upgrades confidence beyond what evidence supports
- Low confidence triggers implicit warnings (e.g., "This view is contested")

---

## Disagreement Detection

The system surfaces genuine disagreements between sources:

1. **Topic Overlap Check**: If multiple chunks discuss the same topic (via keyword overlap)
2. **Semantic Divergence**: But have low similarity scores (< 0.6)
3. **Context Differentiation**: Claude explicitly explains if disagreement is due to different contexts

---

## Output Format

Every response follows this exact structure:

### A. What problem am I actually facing?
Reframes messy input into the true underlying problem. No advice—only clarity.

### B. What do great books agree on here?
Common ground across credible sources, with citations.

### C. Where do great books disagree?
Real disagreements or tradeoffs. Context-aware.

### D. What would I do if this were my company?
1-3 decisive actions. No frameworks. No hedging. Opinionated but evidence-backed.

### E. What should I absolutely NOT do right now?
The most tempting but dangerous mistakes.

---

## Adding New Resources

### Books
1. Place PDF in `resources/books/`
2. Name format: `Book Title - Author Name.pdf`
3. Click "Refresh Database" in the UI or call `POST /refresh`

### Articles
1. Place PDF in `resources/articles/`
2. Name format: `Article Title - Author Name.pdf`
3. Optional: Include URL in brackets: `Title [https://example.com] - Author.pdf`
4. Click "Refresh Database" in the UI or call `POST /refresh`

The refresh system is **idempotent**—it only processes new/modified files.

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | Submit a query, get structured response |
| POST | `/refresh` | Scan and ingest new resources |
| GET | `/stats` | Get vector database statistics |
| GET | `/health` | Health check |
| GET | `/` | Serve frontend |

### Category Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories` | List all categories |
| POST | `/categories` | Add category (requires admin password) |
| DELETE | `/categories/{id}` | Delete category (requires admin password) |
| GET | `/categories/{id}/resources` | List resources in a category |

### Resource Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/resources` | List all resources (optional `?resource_type=book`) |
| DELETE | `/resources/{source_file}` | Delete resource (requires admin password) |
| GET | `/resources/{source_file}/link` | Get article URL |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/verify-admin` | Verify admin password |

### Example: Ask

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "I dont know if I should fire or coach my underperforming CTO"}'
```

---

## CLI Scripts

Manage categories and resources from the command line without starting the server.

### Category Management

```bash
# List all categories
python scripts/manage_categories.py list

# Add a new category
python scripts/manage_categories.py add "Category Name" "Description"

# Delete a category
python scripts/manage_categories.py delete <category-id>
```

### Resource Management

```bash
# List all resources
python scripts/manage_resources.py list

# List only books
python scripts/manage_resources.py list --type book

# Delete a resource
python scripts/manage_resources.py delete "filename.pdf" --type book

# Get article link
python scripts/manage_resources.py get-link "article.pdf"

# Show statistics
python scripts/manage_resources.py stats
```

---

## Project Structure

```
project-root/
├── resources/
│   ├── books/           # Place book PDFs here
│   └── articles/        # Place article PDFs here
├── ingestion/
│   ├── ingest_books.py      # Book PDF processing
│   ├── ingest_articles.py   # Article PDF processing
│   └── refresh_resources.py # Idempotent refresh system
├── backend/
│   ├── main.py          # FastAPI application
│   ├── vector_search.py # Qdrant operations
│   ├── claude_client.py # Claude API integration
│   └── schemas.py       # Pydantic models
├── frontend/
│   ├── index.html       # UI structure
│   ├── styles.css       # Black & white theme
│   └── app.js           # Frontend logic
├── config/
│   └── settings.py      # Configuration
├── requirements.txt
└── README.md
```

---

## Configuration

All settings are in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE` | 500 | Target words per chunk |
| `CHUNK_OVERLAP` | 50 | Overlap words between chunks |
| `TOP_K_RESULTS` | 10 | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | 0.3 | Minimum similarity score |

---

## Troubleshooting

### "No sufficient evidence found"
- Add PDFs to `resources/books/` or `resources/articles/`
- Click "Refresh Database"
- Check that PDFs are readable (not scanned images)

### Connection Error
- Verify `QDRANT_API_KEY` is set
- Check internet connection (Qdrant Cloud requires internet)
- Ensure port 8000 is not in use

### Slow First Query
- First query loads the embedding model (~1-2 seconds)
- Subsequent queries are fast

---

## Constraints

- ✅ **Claude Sonnet 4.5** is the only LLM
- ✅ **Qdrant Cloud** is the only vector database
- ✅ Answers based **only** on retrieved evidence
- ✅ Insufficient evidence → explicit refusal
- ✅ All evidence cited with confidence levels
- ✅ Runs on localhost only

---

## License

For internal use only.
