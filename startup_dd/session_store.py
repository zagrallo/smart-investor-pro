import json
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional
from db import get_pool, init_db

logger = logging.getLogger(__name__)


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


class SessionStore:
    async def _ensure_db(self):
        await init_db()

    async def create_session(self, user_id: str, company_name: str = "") -> str:
        await self._ensure_db()
        pool = await get_pool()
        session_id = uuid.uuid4().hex[:12]
        now = time.time()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO sessions (id, user_id, company_name, status, documents, created_at, updated_at)
                   VALUES ($1, $2, $3, 'active', '[]', $4, $5)""",
                session_id, user_id, company_name, now, now
            )
        logger.info("Session created", extra={"session_id": session_id, "user_id": user_id})
        return session_id

    async def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        await self._ensure_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
            if not row:
                return None
        docs_data = json.loads(row["documents"]) if isinstance(row["documents"], str) else (row["documents"] or [])
        docs = [SessionDoc(**d) for d in docs_data]
        return AnalysisSession(
            id=row["id"],
            user_id=row["user_id"],
            company_name=row.get("company_name", ""),
            status=row.get("status", "active"),
            documents=docs,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            result=row.get("result"),
        )

    async def add_document(self, session_id: str, name: str, content: str) -> bool:
        s = await self.get_session(session_id)
        if not s:
            return False
        s.documents.append(SessionDoc(name=name, content=content, added_at=time.time()))
        s.updated_at = time.time()
        return await self._save(s)

    async def remove_document(self, session_id: str, index: int) -> bool:
        s = await self.get_session(session_id)
        if not s or index < 0 or index >= len(s.documents):
            return False
        s.documents.pop(index)
        s.updated_at = time.time()
        return await self._save(s)

    async def update_company_name(self, session_id: str, company_name: str) -> bool:
        s = await self.get_session(session_id)
        if not s:
            return False
        s.company_name = company_name
        s.updated_at = time.time()
        return await self._save(s)

    async def save_result(self, session_id: str, result: dict) -> bool:
        s = await self.get_session(session_id)
        if not s:
            return False
        s.result = result
        s.status = "completed"
        s.updated_at = time.time()
        return await self._save(s)

    async def delete_session(self, session_id: str) -> bool:
        await self._ensure_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)
            return result != "DELETE 0"

    async def list_sessions(self, user_id: str) -> list[dict]:
        await self._ensure_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 ORDER BY updated_at DESC",
                user_id
            )
        sessions = []
        for row in rows:
            docs_data = json.loads(row["documents"]) if isinstance(row["documents"], str) else (row["documents"] or [])
            docs = [SessionDoc(**d) for d in docs_data]
            s = AnalysisSession(
                id=row["id"], user_id=row["user_id"],
                company_name=row.get("company_name", ""),
                status=row.get("status", "active"),
                documents=docs,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                result=row.get("result"),
            )
            sessions.append(s.to_dict())
        return sessions

    async def _save(self, s: AnalysisSession) -> bool:
        await self._ensure_db()
        pool = await get_pool()
        docs_json = json.dumps([
            {"name": d.name, "content": d.content, "added_at": d.added_at}
            for d in s.documents
        ], ensure_ascii=False)
        result_json = json.dumps(s.result, ensure_ascii=False, default=str) if s.result else None
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE sessions SET company_name=$1, status=$2, documents=$3::jsonb,
                   result=$4::jsonb, updated_at=$5 WHERE id=$6""",
                s.company_name, s.status, docs_json, result_json, s.updated_at, s.id
            )
        return True

    async def cleanup_expired(self) -> int:
        return 0

    async def to_dict(self, session: AnalysisSession) -> dict:
        return session.to_dict()


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
