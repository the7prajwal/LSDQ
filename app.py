"""
Flask backend for the offline RAG app.
Serves a local web UI and API endpoints backed by Ollama + a local vector store.

Everything runs on localhost — no internet required once Ollama and the
models are installed locally.
"""


import os
import sys
import hashlib
import threading

import requests
import subprocess
import json

from flask import Flask, request, jsonify, render_template
import ollama

from loaders import load_folder
from chunker import chunk_segments
from vector_store import PersistentVectorStore
from chat_store import ChatStore


# ---------- PATH HANDLING (works both as script and as PyInstaller .exe) ----------
def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def app_data_path(relative_path):
    appdata = os.getenv("LOCALAPPDATA")
    data_dir = os.path.join(appdata, "LSDQ")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, relative_path)


# ---------- CONFIG ----------
LLM_MODEL = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"
DOCS_FOLDER = app_data_path("documents")
DB_PATH = app_data_path("vector_db")
COLLECTION_NAME = "my_docs"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 4

app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)

_collection = PersistentVectorStore(DB_PATH, COLLECTION_NAME)
_ingest_lock = threading.Lock()
_status = {"state": "idle", "message": ""}
_chats = ChatStore(app_data_path("chats.json"))


def embed_text(text: str):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def file_hash(segments: list) -> str:
    combined = "".join(s["text"] for s in segments)
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def run_ingestion():
    with _ingest_lock:
        _status["state"] = "ingesting"
        _status["message"] = "Scanning documents folder..."

        os.makedirs(DOCS_FOLDER, exist_ok=True)
        documents = load_folder(DOCS_FOLDER)

        if not documents:
            _status["state"] = "idle"
            _status["message"] = f"No documents found in {DOCS_FOLDER}"
            return

        existing = _collection.get(include=["metadatas"])
        existing_hashes = {
            meta["source"]: meta["hash"] for meta in existing["metadatas"]
        } if existing["metadatas"] else {}

        new_chunks, new_ids, new_metadatas = [], [], []

        # Remove chunks for any files that no longer exist in the folder
        current_files = set(documents.keys())
        deleted_files = set(existing_hashes.keys()) - current_files
        for filepath in deleted_files:
            _collection.delete(where={"source": filepath})
        if deleted_files:
            _status["message"] = f"Removed {len(deleted_files)} deleted file(s)."   

        for filepath, segments in documents.items():
            h = file_hash(segments)
            if existing_hashes.get(filepath) == h:
                continue

            _collection.delete(where={"source": filepath})

            chunks = chunk_segments(segments, CHUNK_SIZE, CHUNK_OVERLAP)
            _status["message"] = f"Embedding {os.path.basename(filepath)}..."
            for i, chunk in enumerate(chunks):
                new_chunks.append(chunk["text"])
                new_ids.append(f"{filepath}::{i}")
                new_metadatas.append({
                    "source": filepath,
                    "location": chunk["location"],
                    "hash": h,
                })

        if new_chunks:
            embeddings = [embed_text(c) for c in new_chunks]
            _collection.add(
                ids=new_ids,
                embeddings=embeddings,
                documents=new_chunks,
                metadatas=new_metadatas,
            )
            _status["message"] = f"Added {len(new_chunks)} new chunks."
        else:
            _status["message"] = "All documents already up to date."

        _status["state"] = "idle"

def is_ollama_running():
    try:
        requests.get("http://localhost:11434", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False

def get_installed_models():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout
    except Exception:
        return ""

def pull_model_streaming(model_name):
    process = subprocess.Popen(
        ["ollama", "pull", model_name],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    for line in process.stdout:
        yield line.strip()
    process.wait()


@app.route("/")
def index():
    if not is_ollama_running():
        return render_template("setup.html")
    models = get_installed_models()
    needed = [LLM_MODEL, EMBED_MODEL]
    if any(m not in models for m in needed):
        return render_template("setup.html")
    return render_template("index.html")

@app.route("/setup-status")
def setup_status():
    ollama_ok = is_ollama_running()
    models = get_installed_models()
    needed = [LLM_MODEL, EMBED_MODEL]
    missing = [m for m in needed if m not in models]
    return jsonify({
        "ollama_running": ollama_ok,
        "missing_models": missing
    })

@app.route("/pull-model/<path:model_name>")
def pull_model_route(model_name):
    from flask import Response
    def generate():
        for line in pull_model_streaming(model_name):
            yield f"data: {line}\n\n"
        yield "data: DONE\n\n"
    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/status")
def api_status():
    count = _collection.count()
    return jsonify({
        "state": _status["state"],
        "message": _status["message"],
        "chunk_count": count,
        "docs_folder": DOCS_FOLDER,
    })


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    if _status["state"] == "ingesting":
        return jsonify({"ok": False, "error": "Ingestion already running."}), 409
    thread = threading.Thread(target=run_ingestion, daemon=True)
    thread.start()
    return jsonify({"ok": True})


@app.route("/api/chats", methods=["GET"])
def api_list_chats():
    return jsonify({"ok": True, "chats": _chats.list_chats()})


@app.route("/api/chats", methods=["POST"])
def api_create_chat():
    chat = _chats.create_chat()
    return jsonify({"ok": True, "chat": chat})


@app.route("/api/chats/<chat_id>", methods=["GET"])
def api_get_chat(chat_id):
    chat = _chats.get_chat(chat_id)
    if chat is None:
        return jsonify({"ok": False, "error": "Chat not found."}), 404
    return jsonify({"ok": True, "chat": chat})


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def api_delete_chat(chat_id):
    deleted = _chats.delete_chat(chat_id)
    if not deleted:
        return jsonify({"ok": False, "error": "Chat not found."}), 404
    return jsonify({"ok": True})


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True)
    question = (data or {}).get("question", "").strip()
    chat_id = (data or {}).get("chat_id", "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Empty question."}), 400
    if not chat_id or _chats.get_chat(chat_id) is None:
        return jsonify({"ok": False, "error": "Invalid or missing chat_id."}), 400

    if _collection.count() == 0:
        fallback = ("No documents have been ingested yet. Add files to the "
                    f"'{os.path.basename(DOCS_FOLDER)}' folder and click 'Re-scan documents'.")
        updated_chat = _chats.add_message(chat_id, question, fallback, [])
        return jsonify({
            "ok": True,
            "answer": fallback,
            "sources": [],
            "chat_title": updated_chat["title"] if updated_chat else None,
        })

    query_embedding = embed_text(question)
    results = _collection.query(query_embeddings=[query_embedding], n_results=TOP_K)

    retrieved_chunks = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = []
    sources = []
    seen = set()
    for chunk, meta in zip(retrieved_chunks, metadatas):
        label = f"{os.path.basename(meta['source'])} — {meta['location']}"
        tag = f"[{label}]"
        context_parts.append(f"{tag}\n{chunk}")
        if label not in seen:
            sources.append(label)
            seen.add(label)

    context = "\n\n".join(context_parts)

    prompt = f"""Answer the question using ONLY the context below.
If the answer isn't in the context, say you don't know.

Context:
{context}

Question: {question}

Answer:"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response["message"]["content"]

    updated_chat = _chats.add_message(chat_id, question, answer, sources)

    return jsonify({
        "ok": True,
        "answer": answer,
        "sources": sources,
        "chat_title": updated_chat["title"] if updated_chat else None,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False) 
