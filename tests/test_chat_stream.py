# -*- coding: utf-8 -*-
import unittest
from contextlib import contextmanager

from tests import ensure_project_root

ensure_project_root()

from fastapi.testclient import TestClient

import api


STREAM_DONE_EVENTS = [
    {"type": "token", "text": "我帮你确认一下：下午在福州，带家人，3个人。"},
    {
        "type": "done",
        "slots": {
            "goal": "下午想和老婆孩子在福州附近玩4个小时，孩子5岁，吃家常菜，轻松一点",
            "scene": "family",
            "group_size": "3",
            "city": "福州",
            "time_window": "下午",
            "duration_hours": "4",
            "distance_preference": "近场",
            "travel_mode": "driving",
            "child_age_hint": "5岁",
            "dining_preference": "家常菜",
            "pace_preference": "轻松",
            "special_needs": "",
        },
        "ready_to_plan": True,
        "suggested_replies": ["确认无误，开始规划"],
        "plan_text": "下午想和老婆孩子在福州附近玩4个小时，孩子5岁，吃家常菜，轻松一点",
        "goal": {"scene": "family"},
    },
]


class FakeStreamConversationEngine:
    def reply_stream(self, messages):
        for event in STREAM_DONE_EVENTS:
            yield event


class BrokenStreamConversationEngine:
    def reply_stream(self, messages):
        raise RuntimeError("upstream error")
        yield  # pragma: no cover


@contextmanager
def swap_session_conversation(session_id, engine):
    """临时替换指定会话的对话引擎。"""
    session = api.session_manager.get(session_id)
    if session is None:
        session = api.session_manager.create()
    original = session.conversation
    session.conversation = engine
    try:
        yield session.session_id
    finally:
        session.conversation = original


class TestChatStream(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_stream_emits_done_event_with_goal(self):
        resp = self.client.post("/session")
        sid = resp.json()["session_id"]
        with swap_session_conversation(sid, FakeStreamConversationEngine()):
            response = self.client.post(
                "/chat/stream",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "下午想和老婆孩子在福州附近玩4个小时，孩子5岁，吃家常菜，轻松一点",
                        }
                    ],
                    "session_id": sid,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "done"', response.text)
        self.assertIn('"ready_to_plan": true', response.text)
        self.assertIn('"goal"', response.text)

    def test_stream_emits_error_event_when_llm_unavailable(self):
        resp = self.client.post("/session")
        sid = resp.json()["session_id"]
        with swap_session_conversation(sid, BrokenStreamConversationEngine()):
            response = self.client.post(
                "/chat/stream",
                json={"messages": [{"role": "user", "content": "你好"}], "session_id": sid},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "error"', response.text)
        self.assertIn("服务器或网络异常", response.text)


if __name__ == "__main__":
    unittest.main()
