# -*- coding: utf-8 -*-
import unittest

from tests import ensure_project_root

ensure_project_root()

from meituan_demo.planner import Planner
from meituan_demo.mock_tools import MockToolbox
from meituan_demo.models import Goal, Candidate, Constraint

class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.toolbox = MockToolbox()
        self.planner = Planner(self.toolbox)

    def _family_goal(self):
        return Goal(raw_text="test", scene="family", group_size=3,
                     duration_hours=4, time_window="下午",
                     distance_preference="近场", city="福州",
                     pace_preference="轻松", child_age_hint="5岁",
                     constraints=[Constraint(key="scene",value="family")])

    def _friends_goal(self):
        return Goal(raw_text="test", scene="friends", group_size=4,
                     duration_hours=5, time_window="晚上",
                     distance_preference="可稍远", city="杭州",
                     constraints=[Constraint(key="scene",value="friends")])

    # --- Candidate Scoring ---
    def test_candidate_score_family_boost(self):
        goal = self._family_goal()
        c = Candidate(name="测试", category="activity", tags=["亲子"],
                      duration_minutes=90, area="社区商圈",
                      price_level="medium", family_friendly=True,
                      availability="available", score=8.0, reason="")
        base = self.planner._candidate_score(c, goal)
        c2 = Candidate(name="测试2", category="activity", tags=["社交"],
                       duration_minutes=90, area="核心商圈",
                       price_level="medium", family_friendly=False,
                       availability="available", score=8.0, reason="")
        boost = self.planner._candidate_score(c2, goal)
        self.assertGreater(base, boost)

    # --- Hard Filter ---
    def test_hard_filter_family_excludes_non_friendly(self):
        goal = self._family_goal()
        c = Candidate(name="酒吧", category="activity", tags=["社交"],
                      duration_minutes=120, area="核心商圈",
                      price_level="high", family_friendly=False,
                      availability="available", score=9.0, reason="")
        self.assertFalse(self.planner._hard_filter(c, goal))

    def test_hard_filter_family_keeps_friendly(self):
        goal = self._family_goal()
        c = Candidate(name="亲子乐园", category="activity", tags=["亲子","室内"],
                      duration_minutes=120, area="社区商圈",
                      price_level="medium", family_friendly=True,
                      availability="available", score=9.0, reason="")
        self.assertTrue(self.planner._hard_filter(c, goal))

    def test_hard_filter_qingdan_excludes_zhongkouwei(self):
        goal = self._family_goal()
        goal.dining_preferences = ["清淡饮食"]
        c = Candidate(name="麻辣火锅", category="restaurant", tags=["重口味"],
                      duration_minutes=90, area="核心商圈",
                      price_level="medium", family_friendly=False,
                      availability="available", score=8.0, reason="")
        self.assertFalse(self.planner._hard_filter(c, goal))

    def test_hard_filter_friends_excludes_pure_qinzi(self):
        goal = self._friends_goal()
        c = Candidate(name="婴儿乐园", category="activity", tags=["亲子"],
                      duration_minutes=90, area="社区商圈",
                      price_level="low", family_friendly=True,
                      availability="available", score=8.0, reason="")
        self.assertFalse(self.planner._hard_filter(c, goal))

    def test_hard_filter_indoor_priority_excludes_outdoor_activity(self):
        goal = self._family_goal()
        goal.special_needs = ["室内优先"]
        c = Candidate(name="公园散步", category="activity", tags=["户外", "轻松"],
                      duration_minutes=90, area="近场公园",
                      price_level="low", family_friendly=True,
                      availability="available", score=8.0, reason="")
        self.assertFalse(self.planner._hard_filter(c, goal))

    def test_hard_filter_walking_excludes_too_far_candidate(self):
        goal = self._friends_goal()
        goal.travel_mode = "walking"
        c = Candidate(name="远处桌游局", category="addon", tags=["社交"],
                      duration_minutes=60, area="核心商圈",
                      price_level="medium", family_friendly=False,
                      availability="available", travel_minutes=32, score=8.1, reason="")
        self.assertFalse(self.planner._hard_filter(c, goal))

    # --- Rank ---
    def test_rank_sorts_by_score(self):
        goal = self._family_goal()
        candidates = [
            Candidate(name="A", category="activity", tags=["亲子"], duration_minutes=90,
                      area="社区商圈", price_level="low", family_friendly=True,
                      availability="available", score=7.0, reason=""),
            Candidate(name="B", category="activity", tags=["亲子"], duration_minutes=90,
                      area="社区商圈", price_level="medium", family_friendly=True,
                      availability="available", score=9.0, reason=""),
            Candidate(name="C", category="activity", tags=["亲子"], duration_minutes=90,
                      area="社区商圈", price_level="low", family_friendly=True,
                      availability="available", score=8.0, reason=""),
        ]
        ranked = self.planner._rank_candidates(candidates, goal)
        self.assertEqual(ranked[0].name, "B")
        self.assertEqual(ranked[1].name, "C")
        self.assertEqual(ranked[2].name, "A")

    def test_candidate_score_walking_prefers_nearby(self):
        goal = self._friends_goal()
        goal.travel_mode = "walking"
        near = Candidate(name="近场桌游", category="addon", tags=["社交"],
                         duration_minutes=60, area="同商圈",
                         price_level="low", family_friendly=False,
                         availability="available", travel_minutes=8, score=7.8, reason="")
        far = Candidate(name="远场桌游", category="addon", tags=["社交"],
                        duration_minutes=60, area="核心商圈",
                        price_level="low", family_friendly=False,
                        availability="available", travel_minutes=28, score=7.8, reason="")
        self.assertGreater(self.planner._candidate_score(near, goal), self.planner._candidate_score(far, goal))

    def test_candidate_score_indoor_priority_boosts_indoor(self):
        goal = self._family_goal()
        goal.special_needs = ["室内优先"]
        indoor = Candidate(name="室内乐园", category="activity", tags=["亲子", "室内"],
                           duration_minutes=120, area="社区商圈",
                           price_level="medium", family_friendly=True,
                           availability="available", score=8.0, reason="")
        outdoor = Candidate(name="公园放风", category="activity", tags=["亲子", "户外"],
                            duration_minutes=120, area="近场公园",
                            price_level="low", family_friendly=True,
                            availability="available", score=8.0, reason="")
        self.assertGreater(self.planner._candidate_score(indoor, goal), self.planner._candidate_score(outdoor, goal))

    # --- Build Itinerary ---
    def test_build_plan_produces_itinerary(self):
        goal = self._family_goal()
        plan = self.planner.build_plan(goal)
        self.assertIsNotNone(plan.itinerary)
        self.assertGreater(len(plan.itinerary.stops), 0)
        self.assertGreater(plan.itinerary.score, 0)

    def test_build_plan_alternatives(self):
        goal = self._family_goal()
        plan = self.planner.build_plan(goal)
        self.assertGreater(len(plan.alternatives), 0)
        self.assertEqual(len(plan.alternative_actions), len(plan.alternatives))
        self.assertTrue(all(len(actions) > 0 for actions in plan.alternative_actions))

    def test_build_plan_title_by_scene(self):
        f = self.planner.build_plan(self._family_goal())
        self.assertIn("家庭", f.itinerary.title)
        r = self.planner.build_plan(self._friends_goal())
        self.assertIn("朋友", r.itinerary.title)

    def test_build_plan_primary_and_alternative_actions_match_scene(self):
        goal = self._friends_goal()
        plan = self.planner.build_plan(goal)
        self.assertEqual(plan.actions[-1].action_type, "share")
        self.assertTrue(any(action.action_type == "order" for action in plan.actions))
        if plan.alternative_actions:
            first_alternative_actions = plan.alternative_actions[0]
            self.assertEqual(first_alternative_actions[-1].action_type, "share")
            self.assertTrue(any(action.action_type == "order" for action in first_alternative_actions))

    # --- Score Breakdown ---
    def test_score_breakdown_five_dimensions(self):
        goal = self._family_goal()
        plan = self.planner.build_plan(goal)
        items = plan.itinerary.score_breakdown
        self.assertEqual(len(items), 5)
        labels = [i.label for i in items]
        self.assertIn("路线效率", labels)
        self.assertIn("人群适配", labels)

    # --- Recommendation ---
    def test_recommendation_reason_present(self):
        goal = self._family_goal()
        plan = self.planner.build_plan(goal)
        self.assertTrue(len(plan.itinerary.recommendation_reason) > 0)
        self.assertTrue(len(plan.recommendation_reason) > 0)

if __name__ == "__main__":
    unittest.main()
