# FounderGPT

**Convert chaos into clarity.** An AI-powered advisor for founders navigating tough decisions.

FounderGPT takes messy, unstructured founder input and returns structured, evidence-backed advice using content from curated startup books and articles stored in a vector database. Powered by **Cohere embeddings**, **Qdrant vector search**, and a multi-LLM fallback system (Claude → OpenAI → Gemini).

---

## ✨ Features

- 🔍 **RAG-powered answers** from curated startup literature
- 🔄 **Multi-LLM fallback** (Claude Sonnet 4.5 → GPT-4o → Gemini Flash)
- 📚 **Cohere embeddings & reranking** for high-quality retrieval
- 🎯 **Confidence scoring** for every cited source
- 📖 **Evidence-based responses** with book/article citations
- 🏷️ **Category management** for organizing resources
- 🔐 **Admin authentication** for resource management

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/jaymarvaniya5591/FounderGPT.git
cd FounderGPT
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required
CLAUDE_API_KEY=your_claude_api_key
COHERE_API_KEY=your_cohere_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
ADMIN_PASSWORD=your_admin_password

# Optional (for LLM fallback)
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Add Resources (Books & Articles)

Place PDF files in the resource folders:
- **Books**: `resources/books/` (format: `Title-by-Author Name.pdf`)
- **Articles**: `resources/articles/`

### 5. Run the Server

```bash
python backend/main.py
```

### 6. Open the Application

Navigate to: **http://localhost:8000**

---

## 🏗️ Architecture

```
[User Query]
      ↓
[Query Expansion] → [Cohere Embeddings] → [Qdrant Vector Search]
      ↓
[Cohere Reranker] → [Top 16 Relevant Chunks]
      ↓
[LLM (Claude/OpenAI/Gemini)] ← [System Prompt]
      ↓
[Structured 5-Section Response with Citations]
```

### LLM Fallback Chain
1. **Claude Sonnet 4.5** (primary)
2. **GPT-4o** (fallback 1)
3. **Gemini Flash** (fallback 2)

---

## 📊 Output Format

Every response follows this structure:

### A. What problem am I actually facing?
Reframes messy input into the true underlying problem.

### B. What do great books agree on here?
Common ground across credible sources, with citations.

### C. Where do great books disagree?
Real disagreements or tradeoffs. Context-aware.

### D. What would I do if this were my company?
Decisive, opinionated actions backed by evidence.

### E. What should I absolutely NOT do right now?
The most tempting but dangerous mistakes.

---

## 📁 Project Structure

```
FounderGPT/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── vector_search.py     # Qdrant operations + Cohere
│   ├── llm_gateway.py       # Multi-LLM fallback logic
│   ├── claude_client.py     # Claude API integration
│   ├── openai_client.py     # OpenAI API integration
│   ├── gemini_client.py     # Gemini API integration
│   ├── query_processor.py   # Query expansion
│   └── schemas.py           # Pydantic models
├── frontend/
│   ├── index.html           # UI structure
│   ├── styles.css           # Glassmorphic dark theme
│   └── app.js               # Frontend logic
├── ingestion/
│   ├── ingest_books.py      # Book PDF processing
│   ├── ingest_articles.py   # Article PDF processing
│   └── refresh_resources.py # Idempotent refresh
├── config/
│   ├── settings.py          # Configuration (reads from .env)
│   └── categories.json      # Category definitions
├── resources/
│   ├── books/               # Place book PDFs here (gitignored)
│   └── articles/            # Place article PDFs here (gitignored)
├── scripts/
│   ├── manage_categories.py # CLI category management
│   └── manage_resources.py  # CLI resource management
├── .env.example             # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔧 API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | Submit a query, get structured response |
| POST | `/refresh` | Ingest new resources |
| GET | `/stats` | Vector database statistics |
| GET | `/health` | Health check |

### Category Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories` | List all categories |
| POST | `/categories` | Add category (admin) |
| DELETE | `/categories/{id}` | Delete category (admin) |

### Resource Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/resources` | List all resources |
| DELETE | `/resources/{source_file}` | Delete resource (admin) |

---

## ⚙️ Configuration

Key settings in `config/settings.py` (configured via `.env`):

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `embed-english-v3.0` | Cohere embedding model |
| `EMBEDDING_DIMENSION` | 1024 | Vector dimensions |
| `CHUNK_SIZE` | 700 | Target tokens per chunk |
| `TOP_K_RESULTS` | 16 | Chunks to retrieve |
| `SIMILARITY_THRESHOLD` | 0.28 | Minimum similarity score |
| `ENABLE_RERANKING` | true | Use Cohere reranker |

---

## 🛠️ CLI Scripts

```bash
# Category management
python scripts/manage_categories.py list
python scripts/manage_categories.py add "Category Name" "Description"
python scripts/manage_categories.py delete <category-id>

# Resource management
python scripts/manage_resources.py list
python scripts/manage_resources.py list --type book
python scripts/manage_resources.py stats
```

---

## 🔒 Security Notes

- **API keys** are stored in `.env` (gitignored)
- **Admin password** required for resource/category management
- **Resources** (books/articles) are gitignored to protect copyrighted content

---

## 📝 License

For internal use only.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Copy `.env.example` to `.env` and add your API keys
4. Make your changes
5. Submit a pull request
