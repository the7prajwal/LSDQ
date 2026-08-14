"""
Desktop entry point for the Local Document Assistant.

Starts the Flask backend in a background thread, then opens it inside a
native desktop window (via pywebview) — no browser, no internet required.
This is the file PyInstaller should build into the .exe.
"""

import os
import shutil
import threading
import time
import webview

from app import (
    app,
    run_ingestion,
    is_ollama_running,
    get_installed_models,
    LLM_MODEL,
    EMBED_MODEL,
    DOCS_FOLDER,
)


def start_server():
    # use_reloader must be False — Flask's reloader spawns a second process,
    # which breaks when running from a frozen PyInstaller .exe.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def kick_off_initial_ingest():
    # Don't attempt ingestion until Ollama is actually up and both models
    # are present — avoids a silent failure on a fresh install where the
    # setup screen is still pulling models.
    for _ in range(120):  # wait up to ~2 minutes
        if is_ollama_running():
            models = get_installed_models()
            if LLM_MODEL in models and EMBED_MODEL in models:
                break
        time.sleep(1)
    else:
        return  # gave up waiting — user can trigger ingestion manually later

    run_ingestion()


class Api:
    """Exposed to the frontend as window.pywebview.api.<method>()"""

    def pick_and_add_documents(self):
        file_types = ('Documents (*.pdf;*.docx;*.pptx;*.xlsx;*.txt)',)
        result = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types
        )
        if result:
            os.makedirs(DOCS_FOLDER, exist_ok=True)
            for src in result:
                shutil.copy(src, os.path.join(DOCS_FOLDER, os.path.basename(src)))
            return {"ok": True, "count": len(result)}
        return {"ok": False, "count": 0}

    def open_documents_folder(self):
        os.makedirs(DOCS_FOLDER, exist_ok=True)
        os.startfile(DOCS_FOLDER)
        return {"ok": True}


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    ingest_thread = threading.Thread(target=kick_off_initial_ingest, daemon=True)
    ingest_thread.start()

    api = Api()
    window = webview.create_window(
        "Local Document Assistant",
        "http://127.0.0.1:5000",
        width=1000,
        height=720,
        min_size=(700, 500),
        js_api=api,
    )
    webview.start()