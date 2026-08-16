# LSDQ — Local & Secure Data Query

**A fully offline, privacy-first RAG desktop application for chatting with your documents.**

No cloud APIs. No data leaves your machine. Built for scenarios where sensitive or classified documents can't touch a third-party AI service — but you still want practical, multi-document Q&A.

---

## Why LSDQ?

Most RAG tools assume you're fine sending document chunks to a cloud LLM. LSDQ doesn't make that assumption. Everything — embedding, retrieval, and generation — runs locally on your machine via [Ollama](https://ollama.com). Your documents never leave your device.

## Features

- 📄 **Multi-format ingestion** — PDF, DOCX, PPTX, XLSX, TXT
- 📍 **Location-aware citations** — answers reference the exact page, slide, paragraph, row, or line they came from
- 💬 **Persistent chat sessions** — sidebar with chat history, new chat, per-chat delete
- 🔌 **Fully offline** — no external API calls, no telemetry
- 🖥️ **Native desktop app** — packaged as a standalone Windows installer
- ⚙️ **Zero-config first run** — checks for Ollama, pulls required models, shows live download progress
- 🗂️ **Custom vector store** — lightweight numpy-based implementation (no ChromaDB, no ARM64 build headaches)

## Screenshots

### Chat with your documents, with cited sources
Chat interface with source citations
<img width="800" height="600" alt="chat" src="https://github.com/user-attachments/assets/79a9c5a6-5086-4437-ad9b-49809d73a539" />


*Ask a question and get an answer grounded in your own documents — with exact source paragraphs cited, so you can verify every claim.*

### Multi-format document support
Document indexing
<img width="800" height="600" alt="doc" src="https://github.com/user-attachments/assets/2fe87194-ea00-4a0c-b301-6e31ac6ad8bc" />


*Drop in PDFs, Word docs, PowerPoint slides, and more — LSDQ indexes them locally and shows real-time embedding progress.*

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask |
| Desktop shell | pywebview |
| LLM runtime | Ollama (`llama3.1:8b`) |
| Embeddings | Ollama (`nomic-embed-text`) |
| Vector store | Custom numpy-based implementation |
| Packaging | PyInstaller (onefile) |
| Installer | Inno Setup |

## Getting Started

### Prerequisites
- Windows 10/11 (x64)
- [Ollama](https://ollama.com) (bundled with the installer, or install separately)

### Installation (End Users)
1. Download `LSDQ-Setup.exe` from the [Releases](../../releases) page
2. Run the installer — Ollama will be installed silently if not already present
3. Launch LSDQ from the Start Menu
4. On first run, LSDQ will pull the required models (`llama3.1:8b`, `nomic-embed-text`)
5. Add your documents and start chatting

> **Note:** Windows SmartScreen may flag the installer as unrecognized. Click **More info → Run anyway**. This is expected for unsigned indie software.

### Development Setup

```bash
git clone https://github.com/<your-username>/lsdq.git
cd lsdq
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Requires **x64 Python** (not ARM64) even on ARM-based Windows devices, to avoid native wheel compatibility issues.

## Project Structure

```
lsdq/
├── app.py                 # Flask app entry point
├── vector_store.py         # Custom numpy-based vector store
├── loaders/                 # Document parsers (PDF, DOCX, PPTX, XLSX, TXT)
├── static/                  # Frontend assets (chat UI, setup screen)
├── templates/
│   ├── index.html
│   └── setup.html          # First-run Ollama check + model download UI
├── lsdq.spec                # PyInstaller build spec
├── installer.iss            # Inno Setup script
└── requirements.txt
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for a deeper dive into how the pieces fit together, and [DEPLOYMENT.md](./DEPLOYMENT.md) for build and release instructions.

## Roadmap

- [ ] Code signing to eliminate SmartScreen friction
- [ ] macOS / Linux builds
- [ ] Configurable model selection

## License

MIT (or your preferred license — update this section)
