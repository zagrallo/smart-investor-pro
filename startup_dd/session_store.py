import time
import uuid
import json
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sessions')


@dataclass
class SessionDoc:
    name: str
    content: str
    added_at: float = 0.0


@dataclass
class AnalysisSession:
    id: str
    user_id: str
    company_name: str = ""
    documents: list = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    status: str = "active"
    result: dict | None = None

    @property
    def file_path(self) -> str:
        return os.path.join(DATA_DIR, f"{self.id}.json")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "status": self.status,
            "document_count": len(self.documents),
            "documents": [
                {"name": d.name, "size": len(d.content), "added_at": d.added_at}
                for d in self.documents
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "has_result": self.result is not None,
        }

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "status": self.status,
            "documents": [
                {"name": d.name, "content": d.content, "added_at": d.added_at}
                for d in self.documents
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

    @classmethod
    def load(cls, session_id: str) -> Optional["AnalysisSession"]:
        path = os.path.join(DATA_DIR, f"{session_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load session %s: %s", session_id, e)
            return None
        docs = [SessionDoc(**d) for d in data.get("documents", [])]
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            company_name=data.get("company_name", ""),
            status=data.get("status", "active"),
            documents=docs,
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            result=data.get("result"),
        )


class SessionStore:
    def create_session(self, user_id: str, company_name: str = "") -> str:
        session_id = uuid.uuid4().hex[:12]
        now = time.time()
        session = AnalysisSession(
            id=session_id, user_id=user_id, company_name=company_name,
            documents=[], created_at=now, updated_at=now,
        )
        session.save()
        logger.info("Session created", extra={"session_id": session_id, "user_id": user_id})
        return session_id

    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        return AnalysisSession.load(session_id)

    def add_document(self, session_id: str, name: str, content: str) -> bool:
        s = self.get_session(session_id)
        if not s:
            return False
        s.documents.append(SessionDoc(name=name, content=content, added_at=time.time()))
        s.updated_at = time.time()
        s.save()
        return True

    def remove_document(self, session_id: str, index: int) -> bool:
        s = self.get_session(session_id)
        if not s or index < 0 or index >= len(s.documents):
            return False
        s.documents.pop(index)
        s.updated_at = time.time()
        s.save()
        return True

    def update_company_name(self, session_id: str, company_name: str) -> bool:
        s = self.get_session(session_id)
        if not s:
            return False
        s.company_name = company_name
        s.updated_at = time.time()
        s.save()
        return True

    def save_result(self, session_id: str, result: dict) -> bool:
        s = self.get_session(session_id)
        if not s:
            return False
        s.result = result
        s.status = "completed"
        s.updated_at = time.time()
        s.save()
        return True

    def delete_session(self, session_id: str) -> bool:
        path = os.path.join(DATA_DIR, f"{session_id}.json")
        if os.path.exists(path):
            os.remove(path)
            logger.info("Session deleted", extra={"session_id": session_id})
            return True
        return False

    def list_sessions(self, user_id: str) -> list[dict]:
        sessions = []
        if not os.path.exists(DATA_DIR):
            return sessions
        for fname in os.listdir(DATA_DIR):
            if not fname.endswith(".json"):
                continue
            sid = fname[:-5]
            s = AnalysisSession.load(sid)
            if s and s.user_id == user_id:
                sessions.append(s.to_dict())
        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    def cleanup_expired(self) -> int:
        return 0

    def to_dict(self, session: AnalysisSession) -> dict:
        return session.to_dict()


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
