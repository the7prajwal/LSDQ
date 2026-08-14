"""
Minimal persistent vector store — a lightweight replacement for chromadb.

Why this exists: chromadb's newer versions require compiling a Rust core
plus C-extension dependencies (grpcio, httptools), which fails on Windows
ARM64 without a full Visual Studio C++ toolchain. This store does exactly
what the RAG app needs — store embeddings, persist to disk, do cosine
similarity search — using only numpy (which has prebuilt ARM64 wheels).

API is intentionally shaped like the subset of chromadb's collection API
this app uses, so app.py needed almost no changes.
"""

import os
import json
import numpy as np


class PersistentVectorStore:
    def __init__(self, db_path: str, collection_name: str):
        os.makedirs(db_path, exist_ok=True)
        self._file = os.path.join(db_path, f"{collection_name}.json")
        self._records = []  # list of {id, embedding, document, metadata}
        self._load()

    # ---------- persistence ----------
    def _load(self):
        if os.path.exists(self._file):
            with open(self._file, "r", encoding="utf-8") as f:
                self._records = json.load(f)

    def _save(self):
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self._records, f)

    # ---------- chromadb-like API ----------
    def count(self) -> int:
        return len(self._records)

    def get(self, include=None):
        return {
            "ids": [r["id"] for r in self._records],
            "metadatas": [r["metadata"] for r in self._records],
            "documents": [r["document"] for r in self._records],
        }

    def delete(self, where: dict):
        key, value = next(iter(where.items()))
        before = len(self._records)
        self._records = [r for r in self._records if r["metadata"].get(key) != value]
        if len(self._records) != before:
            self._save()

    def add(self, ids, embeddings, documents, metadatas):
        for _id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            self._records.append({
                "id": _id,
                "embedding": emb,
                "document": doc,
                "metadata": meta,
            })
        self._save()

    def query(self, query_embeddings, n_results: int = 4):
        if not self._records:
            return {"documents": [[]], "metadatas": [[]]}

        query_vec = np.array(query_embeddings[0], dtype=np.float32)
        matrix = np.array([r["embedding"] for r in self._records], dtype=np.float32)

        # cosine similarity
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
        scores = matrix_norm @ query_norm

        top_k = min(n_results, len(self._records))
        top_indices = np.argsort(scores)[::-1][:top_k]

        documents = [self._records[i]["document"] for i in top_indices]
        metadatas = [self._records[i]["metadata"] for i in top_indices]

        return {"documents": [documents], "metadatas": [metadatas]}
