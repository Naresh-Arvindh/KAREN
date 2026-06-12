import time
import datetime
import chromadb
from config.settings import DATA_DIR


class KarenMemory:
    def __init__(self):
        self._client   = chromadb.PersistentClient(path=str(DATA_DIR / "memory"))
        self._convos   = self._client.get_or_create_collection("conversations")
        self._patterns = self._client.get_or_create_collection("patterns")
        self._topics   = self._client.get_or_create_collection("topics")

    def store_conversation(self, summary: str, session_id: str):
        ts = datetime.datetime.now().isoformat()
        self._convos.add(
            documents=[summary],
            metadatas=[{"timestamp": ts, "session": session_id}],
            ids=[f"conv_{session_id}_{int(time.time())}"]
        )

    def store_pattern(self, pattern: str):
        ts = datetime.datetime.now().isoformat()
        self._patterns.add(
            documents=[pattern],
            metadatas=[{"timestamp": ts}],
            ids=[f"pat_{int(time.time())}"]
        )

    def store_topic(self, topic: str):
        ts = datetime.datetime.now().isoformat()
        existing = self._topics.query(query_texts=[topic], n_results=1)
        if existing["documents"] and existing["documents"][0]:
            if existing["distances"] and existing["distances"][0][0] < 0.15:
                return
        self._topics.add(
            documents=[topic],
            metadatas=[{"timestamp": ts}],
            ids=[f"top_{int(time.time())}"]
        )

    def get_relevant_context(self, query: str, n: int = 3) -> str:
        results = []
        for collection, label in [
            (self._convos,   "Past conversation"),
            (self._patterns, "Observed pattern"),
            (self._topics,   "Known topic"),
        ]:
            try:
                r = collection.query(query_texts=[query], n_results=n)
                if r["documents"] and r["documents"][0]:
                    for doc in r["documents"][0]:
                        results.append(f"[{label}]: {doc}")
            except Exception:
                continue
        return "\n".join(results[:5]) if results else ""

    def get_all_topics(self) -> list:
        try:
            r = self._topics.get()
            return r["documents"] if r["documents"] else []
        except Exception:
            return []

    def get_recent_patterns(self, n: int = 5) -> list:
        try:
            r = self._patterns.get(limit=n)
            return r["documents"] if r["documents"] else []
        except Exception:
            return []

    def get_recent_conversations(self, n: int = 10) -> list:
        try:
            r = self._convos.get(limit=n)
            return r["documents"] if r["documents"] else []
        except Exception:
            return []
