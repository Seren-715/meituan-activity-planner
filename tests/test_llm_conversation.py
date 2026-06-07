# -*- coding: utf-8 -*-
import os
import unittest
from unittest.mock import patch

from tests import ensure_project_root

ensure_project_root()

from meituan_demo.llm_conversation import LLMConversationEngine


class TestLLMConversationDefaults(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_API_KEY": "deepseek-test-key",
            "OPENAI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
        },
        clear=False,
    )
    def test_deepseek_defaults_apply_when_only_deepseek_key_exists(self):
        engine = LLMConversationEngine()
        self.assertEqual(engine._model, "deepseek-chat")
        self.assertFalse(engine._llm_disabled)
        self.assertIsNotNone(engine._client)

    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_API_KEY": "deepseek-test-key",
            "OPENAI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
        },
        clear=False,
    )
    def test_confirmation_can_finalize_with_safe_defaults(self):
        engine = LLMConversationEngine()
        result = {
            "assistant_reply": "你大概更想就在附近轻松走走，是吗？",
            "slots": {
                "goal": "散步再去咖啡馆坐坐",
                "scene": "generic",
                "group_size": "1",
                "city": "福州",
                "time_window": "下午",
                "duration_hours": "",
                "distance_preference": "",
                "travel_mode": "",
                "child_age_hint": "",
                "dining_preference": "",
                "pace_preference": "轻松",
                "special_needs": "",
            },
            "ready_to_plan": False,
            "suggested_replies": ["就按这个来"],
            "plan_text": "",
            "goal": None,
        }
        messages = [
            {"role": "user", "content": "今天下午想一个人在福州放松一下，先散步再去咖啡馆坐坐"},
            {"role": "assistant", "content": "你大概更想就在附近轻松走走，是吗？"},
            {"role": "user", "content": "很满意，就按这个来！"},
        ]
        finalized = engine._finalize_confirmation_ready(messages, result)
        self.assertTrue(finalized["ready_to_plan"])
        self.assertIsNotNone(finalized["goal"])
        self.assertEqual(finalized["goal"]["duration_hours"], 4)
        self.assertEqual(finalized["goal"]["distance_preference"], "常规")
        self.assertEqual(finalized["assistant_reply"], "好，那我就按这版先帮你出方案。")

    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_API_KEY": "deepseek-test-key",
            "OPENAI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
        },
        clear=False,
    )
    def test_confirmation_requires_city_before_ready_to_plan(self):
        engine = LLMConversationEngine()
        parsed = {
            "assistant_reply": "我帮你确认一下：朋友聚会，3个人，明天中午，4小时左右，近场活动，对吗？",
            "slots": {
                "goal": "朋友聚会，明天中午想在附近玩一玩",
                "scene": "friends",
                "group_size": "3",
                "city": "",
                "time_window": "中午",
                "duration_hours": "4",
                "distance_preference": "近场",
                "travel_mode": "",
                "child_age_hint": "",
                "dining_preference": "",
                "pace_preference": "",
                "special_needs": "",
            },
            "ready_to_plan": False,
            "suggested_replies": ["没问题，是这样"],
            "plan_text": "",
            "goal": None,
        }
        messages = [
            {"role": "user", "content": "我想约几个朋友出去玩"},
            {"role": "assistant", "content": "你们大概几个人一起呢？"},
            {"role": "user", "content": "3个人"},
            {"role": "assistant", "content": "打算什么时间去？"},
            {"role": "user", "content": "明天中午"},
            {"role": "assistant", "content": "大概玩多久？"},
            {"role": "user", "content": "4小时左右"},
            {"role": "assistant", "content": "你们更偏向近场还是可稍远？"},
            {"role": "user", "content": "近场就好，不想跑太远"},
            {"role": "assistant", "content": "我帮你确认一下：朋友聚会，3个人，明天中午，4小时左右，近场活动，对吗？"},
            {"role": "user", "content": "没问题，是这样"},
        ]

        normalized = engine._normalize_parsed_response(parsed)
        finalized = engine._finalize_confirmation_ready(messages, normalized)

        self.assertFalse(finalized["ready_to_plan"])
        self.assertIsNone(finalized["goal"])
        self.assertEqual(
            finalized["assistant_reply"],
            '还差一个位置信息：你们现在在哪个城市？比如"我在福州"或"从杭州西湖附近出发"都行。',
        )
        self.assertEqual(
            finalized["suggested_replies"],
            ["我在福州", "杭州", "北京"],
        )

    @patch.dict(
        os.environ,
        {
            "DEEPSEEK_API_KEY": "deepseek-test-key",
            "OPENAI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
        },
        clear=False,
    )
    def test_confirmation_accepts_duration_range_and_enters_ready_state(self):
        engine = LLMConversationEngine()
        result = {
            "assistant_reply": "好的！我来帮你确认一下你的需求：一个人、福州、上午、1-2小时，是这样吗？",
            "slots": {
                "goal": "一个人上午在福州逛逛",
                "scene": "generic",
                "group_size": "1",
                "city": "福州",
                "time_window": "上午",
                "duration_hours": "1-2",
                "distance_preference": "常规",
                "travel_mode": "",
                "child_age_hint": "",
                "dining_preference": "",
                "pace_preference": "轻松",
                "special_needs": "",
            },
            "ready_to_plan": False,
            "suggested_replies": ["可以，就这样"],
            "plan_text": "",
            "goal": None,
        }
        messages = [
            {"role": "user", "content": "我想一个人在福州上午出去逛逛"},
            {"role": "assistant", "content": "好的，那你大概想安排多久呢？"},
            {"role": "user", "content": "1-2个小时"},
            {"role": "assistant", "content": "好的！我来帮你确认一下你的需求：场景：一个人出去逛逛，人数：1人，城市：福州，时间：上午，时长：1-2小时。是这样没错吧？"},
            {"role": "user", "content": "可以，就这样"},
        ]

        finalized = engine._finalize_confirmation_ready(messages, result)

        self.assertTrue(finalized["ready_to_plan"])
        self.assertIsNotNone(finalized["goal"])
        self.assertEqual(finalized["goal"]["duration_hours"], 2)
        self.assertEqual(finalized["plan_text"], finalized["goal"]["raw_text"])
        self.assertEqual(finalized["assistant_reply"], "好，那我就按这版先帮你出方案。")


if __name__ == "__main__":
    unittest.main()
