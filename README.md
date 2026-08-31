# Software Knowledge Graph

> **Obsidian for codebases** — an AI-powered platform that turns any GitHub repository into an interactive knowledge graph with semantic search, intelligent code navigation, and an AI agent that answers questions about your code with citations.

---

## Why This Project?

This project combines:

| Domain | Technology |
|---|---|
| Software Engineering | Code parsing, AST extraction, repository analysis |
| Knowledge Graphs | Neo4j, graph traversal, relationship mapping |
| Code Analysis | Tree-sitter, Python/JS/TS parsers |
| RAG | Semantic chunking, vector embeddings, hybrid retrieval |
| Agentic AI | LangGraph, tool calling, multi-step reasoning |
| Graph Traversal | Dependency analysis, impact analysis |
| Automated Testing | Docker sandbox, test execution |

---

## Features

- **Repository Ingestion** — Clone any GitHub repo and extract full AST-level understanding
- **Interactive Knowledge Graph** — Explore classes, functions, modules, and their relationships visually
- **Code Explorer** — Browse code with Monaco editor, click symbols, jump to definitions
- **AI Chat** — Ask questions about the codebase, get answers with clickable source citations
- **Impact Analysis** — Select any symbol and see what would break if you changed it
- **Semantic Search** — Find code by meaning, not just keywords
- **Git History** — Query commit history with natural language
- **Repository Health** — Detect hotspots, coupling, complexity issues

---

## Architecture

```
                       USER
                         │
                         ▼
                  ┌─────────────┐
                  │   Next.js   │
                  │  (JS/React) │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   FastAPI   │
                  │   (Python)  │
                  └──────┬──────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
           ▼             ▼             ▼
      Repository      AI Agent      Search API
      Service        LangGraph
           │             │
           ▼             │
     Code Analyzer       │
     Tree-sitter         │
           │             │
     ┌─────┴─────┐       │
     ▼           ▼       │
   Neo4j       Qdrant ◄──┘
   Graph       Vector DB
     │           │
     └─────┬─────┘
           │
           ▼
        PostgreSQL
           │
           ▼
         Redis
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, JavaScript, React, Tailwind CSS, shadcn/ui |
| Graph Visualization | React Flow |
| Code Editor | Monaco Editor |
| Backend | Python, FastAPI, Pydantic |
| AI Agent | LangGraph, OpenAI-compatible LLM |
| Relational DB | PostgreSQL (SQLAlchemy) |
| Graph DB | Neo4j |
| Vector DB | Qdrant |
| Queue | Redis + RQ |
| Code Parsing | Tree-sitter |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+
- Python 3.12+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/harshbarnwal0101/software-knowledge-graph.git
cd software-knowledge-graph
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Start all services

```bash
docker compose up -d
```

### 4. Run locally (development)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | see `.env.example` |
| `NEO4J_URI` | Neo4j bolt URI | `bolt://localhost:7687` |
| `QDRANT_HOST` | Qdrant hostname | `localhost` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `OPENAI_API_KEY` | LLM API key | — |
| `OPENAI_BASE_URL` | LLM API base URL (OpenAI-compatible) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub token (for private repos) | optional |

---

## Graph Schema

### Nodes

| Node | Properties |
|---|---|
| `Repository` | name, url, language |
| `File` | path, language, lines |
| `Class` | name, file, line |
| `Function` | name, file, line, params |
| `Method` | name, class, line, params |
| `Module` | name, path |
| `Endpoint` | method, path, handler |
| `DatabaseTable` | name, model |
| `Commit` | hash, message, author, date |
| `Developer` | name, email |

### Relationships

| Relationship | From → To |
|---|---|
| `CONTAINS` | Repository/Folder → File/Folder |
| `DEFINES` | File → Class/Function |
| `IMPORTS` | File → Module/File |
| `CALLS` | Function/Method → Function/Method |
| `INHERITS` | Class → Class |
| `IMPLEMENTS` | Class → Interface |
| `USES` | Function → Class/Variable |
| `EXPOSES` | File → Endpoint |
| `ACCESSES` | Function → DatabaseTable |
| `MODIFIED_BY` | File/Function → Commit |
| `DEPENDS_ON` | Module → Module |

---

## API Endpoints

```
GET  /health

POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me

POST /api/repositories
GET  /api/repositories
GET  /api/repositories/{id}
DELETE /api/repositories/{id}
POST /api/repositories/{id}/analyze

GET  /api/repositories/{id}/graph
GET  /api/repositories/{id}/files
GET  /api/repositories/{id}/symbols

POST /api/chat
GET  /api/conversations

GET  /api/repositories/{id}/history
POST /api/repositories/{id}/impact-analysis
GET  /api/repositories/{id}/health
```

---

## Development Phases

- [x] **Phase 1** — Foundation: Next.js, FastAPI, PostgreSQL, Auth, Docker
- [ ] **Phase 2** — Code Understanding: GitHub cloning, Tree-sitter, AST extraction
- [ ] **Phase 3** — Graph: Neo4j, React Flow visualization
- [ ] **Phase 4** — RAG: Embeddings, Qdrant, hybrid retrieval, citations
- [ ] **Phase 5** — AI Agent: LangGraph, tool calling, streaming
- [ ] **Phase 6** — Advanced Intelligence: Impact analysis, architecture explanation
- [ ] **Phase 7** — Code Modification: Patch generation, diff viewer, Docker sandbox

---

## Security Considerations

- Repository content is treated as **untrusted input**
- API keys are stored in environment variables only
- Prompt injection defense: system instructions take priority over repo content
- Code execution only inside Docker containers with resource limits
- User repositories are isolated — users cannot access each other's data

---

## License

MIT
