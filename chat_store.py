"""
Simple local JSON-backed chat history store.

Keeps things dependency-free: chats persist to a single chats.json file
next to the app / .exe, so history survives restarts without needing a
real database.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone


class ChatStore:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        if not os.path.exists(self.path):
            self._write({"chats": {}})

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"chats": {}}

    def _write(self, data: dict):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_chats(self) -> list:
        """Return chat summaries (id, title, created_at), most recent first."""
        with self._lock:
            data = self._read()
        chats = list(data["chats"].values())
        chats.sort(key=lambda c: c["created_at"], reverse=True)
        return [
            {"id": c["id"], "title": c["title"], "created_at": c["created_at"]}
            for c in chats
        ]

    def create_chat(self) -> dict:
        with self._lock:
            data = self._read()
            chat_id = uuid.uuid4().hex[:12]
            chat = {
                "id": chat_id,
                "title": "New chat",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
            }
            data["chats"][chat_id] = chat
            self._write(data)
            return chat

    def get_chat(self, chat_id: str):
        with self._lock:
            data = self._read()
        return data["chats"].get(chat_id)

    def delete_chat(self, chat_id: str) -> bool:
        with self._lock:
            data = self._read()
            if chat_id in data["chats"]:
                del data["chats"][chat_id]
                self._write(data)
                return True
        return False

    def add_message(self, chat_id: str, question: str, answer: str, sources: list):
        """Append a Q/A pair to a chat, auto-titling from the first question."""
        with self._lock:
            data = self._read()
            chat = data["chats"].get(chat_id)
            if chat is None:
                return None

            chat["messages"].append({"role": "user", "content": question})
            chat["messages"].append({
                "role": "bot",
                "content": answer,
                "sources": sources,
            })

            if chat["title"] == "New chat":
                title = question.strip().replace("\n", " ")
                chat["title"] = (title[:47] + "...") if len(title) > 50 else title

            self._write(data)
            return chat
