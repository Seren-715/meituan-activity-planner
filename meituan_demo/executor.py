from __future__ import annotations

from .mock_tools import MockToolbox
from .models import ExecutionAction, ExecutionResult


class Executor:
    def __init__(self, toolbox: MockToolbox) -> None:
        self.toolbox = toolbox

    def run(self, actions: list[ExecutionAction]) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        for action in actions:
            result = self.toolbox.execute(action)
            result.details.setdefault("stage", self._stage_name(action.action_type))
            result.details.setdefault("stage_type", "primary")
            result.details.setdefault("action_target", action.target)
            results.append(result)
            if result.status == "failed":
                results.extend(self._recover(action, result))
        return results

    def _recover(self, action: ExecutionAction, result: ExecutionResult) -> list[ExecutionResult]:
        compensations: list[ExecutionAction] = []
        if action.action_type == "reserve":
            compensations.append(
                ExecutionAction(
                    action_type="reserve",
                    target=f"{action.target}-备选时段",
                    payload={**action.payload, "fallback": "true"},
                )
            )
        elif action.action_type == "queue":
            compensations.append(
                ExecutionAction(
                    action_type="order",
                    target=f"{action.target}-改为先点单",
                    payload={**action.payload, "fallback": "queue_to_order"},
                )
            )
        elif action.action_type == "delivery":
            compensations.append(
                ExecutionAction(
                    action_type="order",
                    target=f"{action.target}-改为到店自取",
                    payload={**action.payload, "fallback": "delivery_to_pickup"},
                )
            )

        recovered: list[ExecutionResult] = []
        for compensation in compensations:
            retry = self.toolbox.execute(compensation)
            retry.details.setdefault("stage", f"补偿{self._stage_name(compensation.action_type)}")
            retry.details.setdefault("stage_type", "compensation")
            retry.details.setdefault("fallback_from", action.action_type)
            if retry.status == "success":
                retry.message = f"{result.message}；已触发补偿动作，{retry.message}"
            if not retry.recovery_hint:
                retry.recovery_hint = "这是系统自动选择的补偿动作，用来保证行程还能继续推进。"
            recovered.append(retry)
        return recovered

    def _stage_name(self, action_type: str) -> str:
        mapping = {
            "reserve": "预约锁位",
            "queue": "排队取号",
            "order": "下单准备",
            "delivery": "附加配送",
            "share": "发送计划",
        }
        return mapping.get(action_type, "动作执行")
