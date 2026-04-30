from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .types import AgentJob, AgentSessionSummary, AgentTurn, utc_now_iso


class AgentSessionStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def _summary_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.json"

    def _turn_log_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "turns.jsonl"

    def _job_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "job.json"

    def create_session(self, title: str) -> AgentSessionSummary:
        session_id = uuid.uuid4().hex[:12]
        session = AgentSessionSummary(id=session_id, title=title or "New Chat")
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        self._summary_path(session_id).write_text(json.dumps(asdict(session), indent=2))
        self._turn_log_path(session_id).touch()
        self._job_path(session_id).write_text(json.dumps(asdict(AgentJob(id=uuid.uuid4().hex[:10], session_id=session_id)), indent=2))
        return session

    def list_sessions(self) -> list[AgentSessionSummary]:
        sessions: list[AgentSessionSummary] = []
        for session_file in sorted(self.root.glob("*/session.json"), reverse=True):
            data = json.loads(session_file.read_text())
            sessions.append(AgentSessionSummary(**data))
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        return sessions

    def get_session(self, session_id: str) -> AgentSessionSummary:
        return AgentSessionSummary(**json.loads(self._summary_path(session_id).read_text()))

    def update_session(self, session: AgentSessionSummary) -> None:
        session.updated_at = utc_now_iso()
        self._summary_path(session.id).write_text(json.dumps(asdict(session), indent=2))

    def append_turn(self, session_id: str, role: str, content: str, **metadata) -> AgentTurn:
        turn = AgentTurn(id=uuid.uuid4().hex[:10], role=role, content=content, metadata=metadata or {})
        with self._turn_log_path(session_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(turn)) + "\n")
        session = self.get_session(session_id)
        session.state = "running" if role == "user" else "idle"
        session.last_message_preview = content[:140]
        self.update_session(session)
        return turn

    def read_turns(self, session_id: str) -> list[AgentTurn]:
        turns: list[AgentTurn] = []
        path = self._turn_log_path(session_id)
        if not path.exists():
            return turns
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            turns.append(AgentTurn(**json.loads(line)))
        return turns

    def get_job(self, session_id: str) -> AgentJob:
        return AgentJob(**json.loads(self._job_path(session_id).read_text()))

    def update_job(self, session_id: str, job: AgentJob) -> None:
        job.updated_at = utc_now_iso()
        self._job_path(session_id).write_text(json.dumps(asdict(job), indent=2))

    def cancel_job(self, session_id: str) -> AgentJob:
        job = self.get_job(session_id)
        job.state = "cancelled"
        self.update_job(session_id, job)
        session = self.get_session(session_id)
        session.state = "cancelled"
        self.update_session(session)
        return job
