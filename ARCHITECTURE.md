# LSDQ Architecture

This document describes how LSDQ is put together: the runtime components, the data flow for ingestion and querying, and the key design decisions behind them.

## High-Level Overview

LSDQ is a **local-first RAG (Retrieval-Augmented Generation) application** packaged as a native Windows desktop app. It has no server-side or cloud component — every process described below runs on the user's own machine.

```
┌─────────────────────────────────────────────────────────────┐
│                        LSDQ.exe                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              pywebview (native window)               │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │         Frontend (HTML/CSS/JS)                │    │    │
│  │  │   setup.html  │  index.html (chat UI)          │    │    │
│  │  └───────────────────┬────────────────────────────┘    │    │
│  └──────────────────────┼───────────────────────────────┘    │
│                          │  js_api / HTTP                      │
│  ┌───────────────────────▼───────────────────────────────┐    │
│  │                  Flask Backend                          │    │
│  │  ┌──────────────┐  ┌────────────────┐  ┌────────────┐  │    │
│  │  │  Doc Loaders  │  │  Vector Store   │  │  Chat Mgmt  │  │    │
│  │  │ PDF/DOCX/PPTX │  │ (numpy-based)   │  │ chats.json  │  │    │
│  │  │ XLSX/TXT      │  │                 │  │             │  │    │
│  │  └──────┬───────┘  └────────┬────────┘  └─────────────┘  │    │
│  └─────────┼───────────────────┼─────────────────────────┘    │
└────────────┼───────────────────┼──────────────────────────────┘
              │                    │
              ▼                    ▼
    ┌───────────────────┐   ┌──────────────────────┐
    │   Ollama Server     │   │  %LOCALAPPDATA%\LSDQ  │
    │  (local process)    │   │  (writable app data)   │
    │ ┌────────────────┐  │   │  - vector store index  │
    │ │ nomic-embed-text│  │   │  - chats.json          │
    │ │ llama3.1:8b     │  │   │  - ingested documents  │
    │ └────────────────┘  │   └──────────────────────┘
    └───────────────────┘
```

## Components

### 1. Desktop Shell — pywebview
Provides the native window chrome and bridges the frontend to Python via `js_api`. Used for:
- Native file picker (document selection)
- "Open Documents Folder" shortcut
- Hosting the Flask app in an embedded webview instead of a browser tab

### 2. Backend — Flask
Runs locally (not exposed to the network) and handles:
- Document ingestion requests
- Chat/query requests, streamed to the frontend
- Server-Sent Events (SSE) for first-run model download progress

### 3. Document Loaders
Format-specific parsers that extract text **and** location metadata so citations can point back to the exact source location:

| Format | Metadata captured |
|---|---|
| PDF | Page number |
| DOCX | Paragraph number |
| PPTX | Slide number |
| XLSX | Row number |
| TXT | Line number |

Extracted text is passed through an **overlapping chunker** before embedding, so context isn't lost at chunk boundaries.

### 4. Vector Store — Custom numpy implementation
LSDQ deliberately avoids ChromaDB. On Windows ARM64, ChromaDB requires compiling native dependencies from source with the ARM64 Visual Studio Build Tools workload — a heavy, fragile requirement for an end-user installer. The custom `vector_store.py`:
- Stores embeddings as numpy arrays
- Performs similarity search directly (cosine similarity)
- Persists to disk under `%LOCALAPPDATA%\LSDQ`
- Has zero compiled dependencies, keeping the PyInstaller build simple and portable

### 5. LLM Runtime — Ollama
Ollama runs as a separate local process/service and is used for two distinct roles:

| Model | Role |
|---|---|
| `nomic-embed-text` | Generates embeddings for chunks and queries |
| `llama3.1:8b` | Generates the final answer given retrieved context |

**Important distinction:** LSDQ performs RAG, not fine-tuning. The `llama3.1:8b` model weights are never modified — documents are chunked, embedded, and retrieved at query time, then injected into the model's context window as part of the prompt.

### 6. Chat Persistence
Chat sessions (messages, citations, timestamps) are stored in `chats.json` under the app data directory. The sidebar UI reads/writes this file to support multiple chat threads, history, and per-chat deletion.

## Data Flow

### Ingestion
```
User selects document(s)
   → Loader parses file, extracts text + location metadata
   → Chunker splits text into overlapping chunks
   → Each chunk sent to Ollama (nomic-embed-text) for embedding
   → Embedding + chunk + metadata stored in vector_store
```

### Query
```
User submits a question
   → Question embedded via nomic-embed-text
   → Vector store returns top-N most similar chunks (cosine similarity)
   → Chunks + question assembled into a prompt
   → Prompt sent to llama3.1:8b via Ollama
   → Response streamed back to the UI, with citations
     mapped to the source chunks' location metadata
```

## Path Handling

Packaged desktop apps must distinguish between **read-only bundled assets** and **writable runtime data**:

- `resource_path()` — resolves paths to assets bundled inside the PyInstaller executable (read-only, changes only on reinstall)
- `app_data_path()` — resolves paths to `%LOCALAPPDATA%\LSDQ` for anything written at runtime (vector store, chat history, ingested document copies)

Writable data is never written next to `LSDQ.exe` itself — that directory may be read-only (e.g. under `Program Files`) and isn't meant to hold user state.

## First-Run Flow

```
LSDQ.exe launches
   → setup.html checks: is Ollama running / installed?
      ├── No  → prompt/install Ollama, poll until available
      └── Yes → continue
   → Check for required models (llama3.1:8b, nomic-embed-text)
      ├── Missing → stream pull progress via SSE
      └── Present → continue
   → Redirect to index.html (main chat UI)
```

This flow exists to solve a real failure mode encountered during development: ingestion would fail silently on fresh installs if Ollama or its models weren't ready yet. The fix was to explicitly gate ingestion behind a readiness check rather than assuming Ollama is available.

## Key Design Decisions

| Decision | Reasoning |
|---|---|
| Custom numpy vector store instead of ChromaDB | Avoids ARM64 compilation requirements; keeps PyInstaller bundling simple |
| x64 Python instead of ARM64 Python | Avoids native wheel incompatibility, at a small performance cost |
| pywebview instead of Electron | Lighter weight, uses the OS's native webview, smaller installer |
| Ollama as external process instead of embedded inference | Reuses a mature, maintained local LLM runtime instead of reinventing model serving |
| Explicit Ollama/model readiness check before ingestion | Prevents silent ingestion failures on fresh installs |
