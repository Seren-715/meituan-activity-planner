# -*- coding: utf-8 -*-
import unittest

from tests import ensure_project_root

ensure_project_root()

from meituan_demo.executor import Executor
from meituan_demo.mock_tools import MockToolbox
from meituan_demo.models import ExecutionAction, ExecutionResult

class TestExecutor(unittest.TestCase):
    def setUp(self):
        self.toolbox = MockToolbox()
        self.executor = Executor(self.toolbox)

    def _action(self, action_type, target="test-target", payload=None):
        return ExecutionAction(action_type=action_type, target=target,
                               payload=payload or {})

    # --- Normal Execution ---
    def test_all_actions_succeed_in_normal_scenario(self):
        actions = [self._action("reserve"), self._action("queue"),
                   self._action("order"), self._action("share")]
        results = self.executor.run(actions)
        for r in results:
            self.assertEqual(r.status, "success",
                             f"{r.action_type} should succeed: {r.message}")

    def test_execution_result_has_reference_id(self):
        results = self.executor.run([self._action("reserve")])
        self.assertTrue(len(results[0].reference_id) > 0)

    def test_execution_result_has_stage(self):
        results = self.executor.run([self._action("queue")])
        self.assertIn("stage", results[0].details)
        self.assertEqual(results[0].details["stage"], "排队取号")
        self.assertEqual(results[0].details["stage_type"], "primary")

    # --- Failure + Compensation ---
    def test_reserve_timeout_triggers_compensation(self):
        self.toolbox.scenario = "reserve_timeout"
        results = self.executor.run([self._action("reserve")])
        self.assertEqual(results[0].status, "failed")
        self.assertEqual(results[0].action_type, "reserve")
        # Compensation should have been triggered
        self.assertGreater(len(results), 1)
        comp = results[1]
        self.assertEqual(comp.action_type, "reserve")
        self.assertIn("备选时段", comp.target)

    def test_queue_failure_triggers_order_compensation(self):
        self.toolbox.scenario = "partial_failure"
        results = self.executor.run([self._action("queue")])
        self.assertEqual(results[0].status, "failed")
        self.assertGreater(len(results), 1)
        comp = results[1]
        self.assertEqual(comp.action_type, "order")
        self.assertIn("先点单", comp.target)
        self.assertEqual(comp.details["stage_type"], "compensation")
        self.assertEqual(comp.details["fallback_from"], "queue")

    def test_delivery_failure_triggers_pickup_compensation(self):
        self.toolbox.scenario = "partial_failure"
        results = self.executor.run([self._action("delivery")])
        self.assertEqual(results[0].status, "failed")
        self.assertGreater(len(results), 1)
        comp = results[1]
        self.assertEqual(comp.action_type, "order")
        self.assertIn("自取", comp.target)

    # --- Share always succeeds ---
    def test_share_always_succeeds(self):
        self.toolbox.scenario = "partial_failure"
        results = self.executor.run([self._action("share")])
        self.assertEqual(results[0].status, "success")
        self.assertEqual(results[0].action_type, "share")

    # --- Unknown action ---
    def test_unknown_action_fails(self):
        results = self.executor.run([self._action("unknown_type")])
        self.assertEqual(results[0].status, "failed")
        self.assertIn("未识别", results[0].message)

    # --- Mixed success/failure ---
    def test_mixed_actions(self):
        self.toolbox.scenario = "reserve_timeout"
        actions = [self._action("reserve"), self._action("share")]
        results = self.executor.run(actions)
        statuses = [r.status for r in results]
        self.assertIn("failed", statuses)
        self.assertIn("success", statuses)
        # reserve failed + compensation, share succeeded
        self.assertGreater(len(results), 2)

    # --- Stage names ---
    def test_stage_names(self):
        self.assertEqual(self.executor._stage_name("reserve"), "预约锁位")
        self.assertEqual(self.executor._stage_name("queue"), "排队取号")
        self.assertEqual(self.executor._stage_name("order"), "下单准备")
        self.assertEqual(self.executor._stage_name("delivery"), "附加配送")
        self.assertEqual(self.executor._stage_name("share"), "发送计划")

    def test_stage_name_unknown(self):
        self.assertEqual(self.executor._stage_name("nonexistent"), "动作执行")

if __name__ == "__main__":
    unittest.main()
