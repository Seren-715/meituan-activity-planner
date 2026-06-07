# -*- coding: utf-8 -*-
import unittest
from contextlib import contextmanager

from tests import ensure_project_root

ensure_project_root()

from fastapi.testclient import TestClient

import api


READY_CHAT_PAYLOAD = {
    "assistant_reply": "我帮你确认一下：下午在福州，带家人，3个人，孩子差不多5岁，玩4个小时左右，不想跑太远，想吃家常菜，节奏轻松一点。这样对吗？",
    "slots": {
        "goal": "下午想和老婆还有5岁孩子在福州附近玩4个小时，吃家常菜，轻松一点",
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
    "suggested_replies": ["确认无误，开始规划", "再改一点"],
    "plan_text": "下午想和老婆还有5岁孩子在福州附近玩4个小时，吃家常菜，轻松一点",
    "goal": {
        "raw_text": "下午想和老婆还有5岁孩子在福州附近玩4个小时，吃家常菜，轻松一点",
        "scene": "family",
        "group_size": 3,
        "duration_hours": 4,
        "time_window": "下午",
        "distance_preference": "近场",
        "city": "福州",
        "origin_name": "",
        "origin_lat": None,
        "origin_lng": None,
        "travel_mode": "driving",
        "child_age_hint": "5岁",
        "share_target": "家人",
        "pace_preference": "轻松",
        "preferences": ["亲子友好", "照顾儿童节奏", "少折腾"],
        "dining_preferences": ["家常菜"],
        "special_needs": ["适合儿童", "儿童年龄约5岁"],
        "constraints": [
            {"key": "scene", "value": "family"},
            {"key": "group_size", "value": "3"},
            {"key": "duration_hours", "value": "4"},
            {"key": "time_window", "value": "下午"},
            {"key": "distance_preference", "value": "近场"},
            {"key": "pace_preference", "value": "轻松"},
            {"key": "travel_mode", "value": "driving"},
            {"key": "city", "value": "福州"},
            {"key": "child_age_hint", "value": "5岁"},
            {"key": "dining_preferences", "value": "家常菜"},
        ],
    },
}


class FakeConversationEngine:
    def reply(self, messages):
        return READY_CHAT_PAYLOAD


class BrokenConversationEngine:
    def reply(self, messages):
        raise RuntimeError("upstream error")


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


class TestApiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_chat_returns_goal_when_ready(self):
        # 先创建会话
        resp = self.client.post("/session")
        sid = resp.json()["session_id"]
        with swap_session_conversation(sid, FakeConversationEngine()):
            response = self.client.post(
                "/chat",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "下午想和老婆还有5岁孩子在福州附近玩4个小时，吃家常菜，轻松一点",
                        }
                    ],
                    "session_id": sid,
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ready_to_plan"])
        self.assertIsNotNone(payload["goal"])
        self.assertEqual(payload["goal"]["scene"], "family")
        self.assertEqual(payload["goal"]["group_size"], 3)

    def test_plan_direct_accepts_goal_from_chat(self):
        goal = READY_CHAT_PAYLOAD["goal"]
        self.assertIsNotNone(goal)
        response = self.client.post("/plan/direct", json=goal)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("itinerary", payload)
        self.assertGreater(len(payload["itinerary"]["stops"]), 0)
        self.assertGreater(len(payload["actions"]), 0)
        self.assertIn("alternative_actions", payload)
        self.assertEqual(len(payload["alternative_actions"]), len(payload["alternatives"]))

    def test_chat_returns_503_when_llm_unavailable(self):
        # 先创建会话
        resp = self.client.post("/session")
        sid = resp.json()["session_id"]
        with swap_session_conversation(sid, BrokenConversationEngine()):
            response = self.client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "你好"}], "session_id": sid},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("对话服务暂时不可用", response.text)


if __name__ == "__main__":
    unittest.main()
