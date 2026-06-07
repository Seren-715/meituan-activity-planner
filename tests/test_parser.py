# -*- coding: utf-8 -*-
import unittest

from tests import ensure_project_root

ensure_project_root()

from meituan_demo.parser import GoalParser

class TestGoalParser(unittest.TestCase):
    def setUp(self):
        self.parser = GoalParser()

    # --- Scene ---
    def test_scene_family(self):
        for t in ["和老婆出去", "带孩子玩", "家人聚会", "亲子活动"]:
            self.assertEqual(self.parser.parse(t).scene, "family")

    def test_scene_friends(self):
        for t in ["和朋友聚会", "同事聚餐", "闺蜜逛街"]:
            self.assertEqual(self.parser.parse(t).scene, "friends")

    def test_scene_generic(self):
        self.assertEqual(self.parser.parse("出去转转").scene, "generic")

    # --- Group Size ---
    def test_group_size_digits(self):
        self.assertEqual(self.parser.parse("5个人一起").group_size, 5)

    def test_group_size_chinese(self):
        self.assertEqual(self.parser.parse("三个人").group_size, 3)

    def test_group_size_default_family(self):
        g = self.parser.parse("带老婆和孩子出去")
        self.assertEqual(g.scene, "family")
        self.assertEqual(g.group_size, 3)

    def test_group_size_default_friends(self):
        g = self.parser.parse("和朋友聚餐")
        self.assertEqual(g.scene, "friends")
        self.assertEqual(g.group_size, 4)

    def test_group_size_patterns(self):
        # 一家X口 pattern
        self.assertEqual(self.parser.parse("一家三口").group_size, 3)
        self.assertEqual(self.parser.parse("一家四口").group_size, 4)
        self.assertEqual(self.parser.parse("一家五口").group_size, 5)
        # X口之家 pattern
        self.assertEqual(self.parser.parse("三口之家").group_size, 3)
        self.assertEqual(self.parser.parse("四口之家").group_size, 4)
        # 夫妻/两口子
        self.assertEqual(self.parser.parse("夫妻俩").group_size, 2)
        self.assertEqual(self.parser.parse("两口子").group_size, 2)
        # 两大一小
        self.assertEqual(self.parser.parse("两大一小").group_size, 3)

    # --- Duration ---
    def test_duration_exact(self):
        self.assertEqual(self.parser.parse("4个小时").duration_hours, 4)

    def test_duration_vague(self):
        self.assertEqual(self.parser.parse("半天时间").duration_hours, 5)

    def test_duration_default(self):
        self.assertEqual(self.parser.parse("随便逛逛").duration_hours, 5)

    # --- Time Window ---
    def test_time_window(self):
        self.assertEqual(self.parser.parse("上午出发").time_window, "上午")
        self.assertEqual(self.parser.parse("下午").time_window, "下午")
        self.assertEqual(self.parser.parse("晚上").time_window, "晚上")
        self.assertEqual(self.parser.parse("中午").time_window, "中午")

    def test_time_window_default(self):
        self.assertEqual(self.parser.parse("出发").time_window, "下午")

    # --- Distance ---
    def test_distance_nearby(self):
        for t in ["别太远", "离家近", "附近", "不想跑太远"]:
            self.assertEqual(self.parser.parse(t).distance_preference, "近场")

    def test_distance_far(self):
        self.assertEqual(self.parser.parse("远一点也行").distance_preference, "可稍远")

    def test_distance_default(self):
        self.assertEqual(self.parser.parse("随便").distance_preference, "常规")

    # --- City ---
    def test_city(self):
        self.assertEqual(self.parser.parse("", {"city": "福州"}).city, "福州")
        self.assertEqual(self.parser.parse("", {"city": "上海"}).city, "上海")

    # --- Child Age ---
    def test_child_age(self):
        self.assertEqual(self.parser.parse("孩子5岁").child_age_hint, "5岁")

    def test_child_age_unset(self):
        self.assertEqual(self.parser.parse("出去").child_age_hint, "")

    # --- Dining ---
    def test_dining(self):
        self.assertIn("火锅", self.parser.parse("吃火锅").dining_preferences)

    def test_dining_qingdan(self):
        g = self.parser.parse("清淡减脂")
        self.assertIn("清淡饮食", g.special_needs)

    # --- Pace ---
    def test_pace(self):
        self.assertEqual(self.parser.parse("轻松一点").pace_preference, "轻松")
        self.assertEqual(self.parser.parse("紧凑").pace_preference, "紧凑")

    # --- Travel Mode ---
    def test_travel_walking(self):
        g = self.parser.parse("步行", {"travel_mode": "walking"})
        self.assertEqual(g.travel_mode, "walking")

    def test_travel_default(self):
        self.assertEqual(self.parser.parse("出门").travel_mode, "driving")

    # --- Full Integration ---
    def test_full_family(self):
        g = self.parser.parse("下午想和老婆还有5岁孩子去公园，在福州离家近4个小时吃家常菜轻松")
        self.assertEqual(g.scene, "family")
        self.assertEqual(g.group_size, 3)
        self.assertEqual(g.duration_hours, 4)
        self.assertEqual(g.time_window, "下午")
        self.assertEqual(g.distance_preference, "近场")
        self.assertEqual(g.city, "")  # GoalParser gets city from context only
        self.assertEqual(g.child_age_hint, "5岁")
        self.assertEqual(g.pace_preference, "轻松")

    def test_constraints_structure(self):
        g = self.parser.parse("下午带孩子去福州4个小时轻松")
        self.assertTrue(len(g.constraints) >= 7)
        keys = [c.key for c in g.constraints]
        self.assertIn("scene", keys)
        self.assertIn("group_size", keys)

if __name__ == "__main__":
    unittest.main()
