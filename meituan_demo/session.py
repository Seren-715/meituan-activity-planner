"""会话管理模块。

为每个用户创建独立的 Agent 和对话引擎实例，避免多用户时共享状态。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .agent import LocalActivityAgent
from .llm_conversation import LLMConversationEngine


@dataclass
class Session:
    """单个用户会话，持有独立的 agent 和对话引擎。"""
    session_id: str
    agent: LocalActivityAgent = field(default_factory=LocalActivityAgent)
    conversation: LLMConversationEngine = field(default_factory=LLMConversationEngine)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def touch(self) -> None:
        """更新最后活跃时间。"""
        self.last_active = time.time()


class SessionManager:
    """内存级会话管理器。"""

    def __init__(self, max_sessions: int = 100, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, Session] = {}
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds

    def create(self) -> Session:
        """创建新会话，清理过期会话后返回。"""
        self._cleanup()
        session_id = uuid.uuid4().hex[:12]
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """获取会话，不存在或已过期返回 None。"""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() - session.last_active > self._ttl_seconds:
            del self._sessions[session_id]
            return None
        session.touch()
        return session

    def get_or_create(self, session_id: str | None) -> Session:
        """获取已有会话，不存在时自动创建。"""
        if session_id:
            session = self.get(session_id)
            if session is not None:
                return session
        return self.create()

    def _cleanup(self) -> None:
        """清理过期会话，超出上限时淘汰最旧的。"""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_active > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]

        # 如果仍然超出上限，淘汰最旧的
        while len(self._sessions) > self._max_sessions:
            oldest = min(self._sessions, key=lambda sid: self._sessions[sid].last_active)
            del self._sessions[oldest]

    @property
    def count(self) -> int:
        return len(self._sessions)
