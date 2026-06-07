# -*- coding: utf-8 -*-
import unittest

from tests import ensure_project_root

ensure_project_root()

from meituan_demo.conversation import ConversationOrchestrator, ConversationSlots

class TestConversationStateMachine(unittest.TestCase):
    def setUp(self):
        self.c = ConversationOrchestrator()

    def _slots(self, **kwargs):
        s = ConversationSlots()
        for k, v in kwargs.items():
            setattr(s, k, v)
        return s

    # --- 复述 (Recap) ---
    def test_recap_natural_language(self):
        slots = self._slots(city="福州", time_window="下午", scene="family",
                            group_size="3", child_age_hint="5岁",
                            duration_hours="4", distance_preference="近场",
                            dining_preference="家常菜", pace_preference="轻松")
        recap = self.c._build_recap(slots)
        self.assertIn("我帮你理一下哈", recap)
        self.assertIn("我理解的对吗", recap)
        self.assertNotIn("：", recap)  # no more colon-delimited format
        self.assertIn("差不多", recap)
        self.assertIn("左右", recap)

    def test_recap_empty_returns_hint(self):
        slots = ConversationSlots()
        recap = self.c._build_recap(slots)
        self.assertIn("信息还不够完整", recap)

    # --- 改口检测 (Change Detection) ---
    def test_detect_slot_changes_finds_time_change(self):
        prev = self._slots(time_window="下午")
        curr = self._slots(time_window="晚上")
        changes = self.c._detect_slot_changes(prev, curr, "算了还是晚上吧")
        self.assertIn("time_window", changes)
        self.assertEqual(changes["time_window"], ("下午", "晚上"))

    def test_detect_slot_changes_ignores_goal(self):
        prev = self._slots(goal="old text")
        curr = self._slots(goal="newer longer text")
        changes = self.c._detect_slot_changes(prev, curr, "newer longer text")
        self.assertNotIn("goal", changes)

    def test_detect_slot_changes_empty_prev(self):
        prev = ConversationSlots()
        curr = self._slots(time_window="下午")
        changes = self.c._detect_slot_changes(prev, curr, "下午")
        self.assertEqual(len(changes), 0)

    def test_detect_slot_changes_requires_domain_keyword(self):
        prev = self._slots(time_window="下午", duration_hours="4")
        curr = self._slots(time_window="下午", duration_hours="6")
        # Message doesn't mention hours
        changes = self.c._detect_slot_changes(prev, curr, "就下午吧")
        self.assertNotIn("duration_hours", changes)

    # --- 改口确认 (Change Ack) ---
    def test_change_ack_format(self):
        changes = {"time_window": ("下午", "晚上")}
        ack = self.c._build_change_ack(changes, self._slots())
        self.assertIn("「", ack)
        self.assertIn("」", ack)
        self.assertNotIn("【", ack)
        self.assertNotIn("】", ack)
        self.assertIn("改", ack)

    def test_change_ack_empty(self):
        ack = self.c._build_change_ack({}, self._slots())
        self.assertIn("记下了", ack)

    # --- 冲突检测 (Conflict Detection) ---
    def test_conflict_night_long_hours(self):
        slots = self._slots(time_window="晚上", duration_hours="5")
        c = self.c._detect_conflicts(slots)
        self.assertIsNotNone(c)
        self.assertIn("很晚", c)

    def test_conflict_family_compact(self):
        slots = self._slots(scene="family", pace_preference="紧凑")
        c = self.c._detect_conflicts(slots)
        self.assertIsNotNone(c)
        self.assertIn("太满", c)

    def test_conflict_nearby_large_group(self):
        slots = self._slots(distance_preference="近场", group_size="5")
        c = self.c._detect_conflicts(slots)
        self.assertIsNotNone(c)
        self.assertIn("近", c)

    def test_conflict_none(self):
        slots = self._slots(scene="family", pace_preference="轻松",
                            time_window="下午", duration_hours="3")
        self.assertIsNone(self.c._detect_conflicts(slots))

    # --- 小闲聊分类 (Smalltalk) ---
    def test_smalltalk_greeting(self):
        self.assertEqual(self.c._classify_smalltalk("你好"), "greeting")
        self.assertEqual(self.c._classify_smalltalk("在吗"), "greeting")

    def test_smalltalk_thanks(self):
        self.assertEqual(self.c._classify_smalltalk("谢谢"), "thanks")

    def test_smalltalk_filler(self):
        self.assertEqual(self.c._classify_smalltalk("不知道"), "filler")
        self.assertEqual(self.c._classify_smalltalk("随便"), "filler")

    def test_smalltalk_confused(self):
        self.assertEqual(self.c._classify_smalltalk("?"), "confused")
        self.assertEqual(self.c._classify_smalltalk("？？"), "confused")

    # --- 意图检测 (Intent) ---
    def test_meaningful_intent_detected(self):
        self.assertTrue(self.c._has_meaningful_intent("下午想带孩子去公园"))

    def test_no_meaningful_intent(self):
        self.assertFalse(self.c._has_meaningful_intent("你好"))
        self.assertFalse(self.c._has_meaningful_intent("谢谢"))

    # --- Full Reply Flow ---
    def test_reply_with_change(self):
        msgs = [
            {"role":"user","content":"下午想出去"},
            {"role":"user","content":"算了还是晚上吧"}
        ]
        r = self.c.reply(msgs)
        self.assertIn("改", r["assistant_reply"])
        self.assertIn("晚上", r["assistant_reply"])

    def test_reply_with_conflict(self):
        msgs = [
            {"role":"user","content":"晚上想出去安排6个小时带孩子节奏紧凑"}
        ]
        r = self.c.reply(msgs)
        self.assertIn("提醒", r["assistant_reply"])

    def test_reply_ready_recap(self):
        msgs = [{"role":"user","content":"下午想和老婆还有5岁孩子去公园，在福州离家近4个小时家常菜轻松"}]
        r = self.c.reply(msgs)
        self.assertTrue(r["ready_to_plan"])
        self.assertIn("我理解的对吗", r["assistant_reply"])
        self.assertIsNotNone(r["goal"])
        self.assertEqual(r["goal"]["scene"], "family")
        self.assertEqual(r["goal"]["group_size"], 3)
        self.assertTrue(any(item["key"] == "distance_preference" for item in r["goal"]["constraints"]))

    def test_ready_goal_contains_special_needs(self):
        msgs = [{"role":"user","content":"下午想带5岁孩子在福州附近玩4个小时，想室内一点，停车方便，吃家常菜，轻松一点"}]
        r = self.c.reply(msgs)
        self.assertTrue(r["ready_to_plan"])
        self.assertIn("室内优先", r["goal"]["special_needs"])
        self.assertIn("停车方便", r["goal"]["special_needs"])

    def test_goal_not_ready_when_core_slots_missing(self):
        msgs = [{"role":"user","content":"想和朋友出去"}]
        r = self.c.reply(msgs)
        self.assertFalse(r["ready_to_plan"])
        self.assertIsNone(r["goal"])

    def test_reply_greeting(self):
        msgs = [{"role":"user","content":"你好"}]
        r = self.c.reply(msgs)
        self.assertFalse(r["ready_to_plan"])
        self.assertTrue(len(r["assistant_reply"]) > 5)

if __name__ == "__main__":
    unittest.main()
