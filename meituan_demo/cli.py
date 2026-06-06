from __future__ import annotations

import sys

from .agent import LocalActivityAgent
from .models import AgentOutput, Itinerary, PlanningOutput


def main() -> int:
    agent = LocalActivityAgent()
    user_text = _get_user_text(sys.argv[1:])
    planning = agent.plan(user_text)
    _print_planning(planning)

    confirmed = _confirm()
    if not confirmed:
        print("\n已取消执行，当前仅展示规划结果。")
        return 0

    output = agent.execute(planning)
    _print_execution(output)
    return 0


def _get_user_text(args: list[str]) -> str:
    if args:
        return " ".join(args).strip()
    print("请输入一句活动目标：")
    return input("> ").strip() or "今天下午想和朋友轻松出去玩和吃饭，别太折腾"


def _print_planning(planning: PlanningOutput) -> None:
    goal = planning.goal
    itinerary = planning.itinerary

    print("\n=== 结构化目标 ===")
    print(f"场景: {goal.scene}")
    print(f"人数: {goal.group_size}")
    print(f"时段: {goal.time_window}")
    print(f"期望时长: {goal.duration_hours} 小时")
    print(f"距离偏好: {goal.distance_preference}")
    print(f"节奏偏好: {goal.pace_preference}")
    print(f"分享对象: {goal.share_target}")
    print(f"儿童年龄: {goal.child_age_hint or '未指定'}")
    print(f"偏好: {', '.join(goal.preferences) if goal.preferences else '无'}")
    print(f"餐饮偏好: {', '.join(goal.dining_preferences) if goal.dining_preferences else '无'}")
    print(f"特殊需求: {', '.join(goal.special_needs) if goal.special_needs else '无'}")

    print("\n=== 主推荐方案 ===")
    _print_itinerary(itinerary)

    if planning.alternatives:
        print("\n=== 备选方案 ===")
        for index, alternative in enumerate(planning.alternatives, start=1):
            print(f"\n备选 {index}:")
            _print_itinerary(alternative)


def _confirm() -> bool:
    print("\n是否确认并执行关键动作？输入 y 确认，其他任意键取消。")
    return input("> ").strip().lower() == "y"


def _print_execution(output: AgentOutput) -> None:
    print("\n=== 执行结果 ===")
    for result in output.execution_results:
        print(
            f"- {result.action_type} | {result.target} | {result.status} | "
            f"{result.message} | 凭证: {result.reference_id}"
        )
        if result.recovery_hint:
            print(f"  补偿建议: {result.recovery_hint}")

    if output.summary:
        print("\n=== 执行摘要 ===")
        for item in output.summary:
            print(f"- {item}")

    print("\n=== 分享文案 ===")
    print(output.share_text)


def _print_itinerary(itinerary: Itinerary) -> None:
    print(f"{itinerary.title} | 评分 {itinerary.score:.1f} | 总时长 {itinerary.total_minutes} 分钟")
    for stop in itinerary.stops:
        print(
            f"- {stop.start_time} | {stop.title} | {stop.duration_minutes} 分钟 | "
            f"{stop.location} | {stop.note}"
        )

    if itinerary.alerts:
        print("提醒:")
        for alert in itinerary.alerts:
            print(f"- {alert}")

    print("方案理由:")
    for reason in itinerary.rationale:
        print(f"- {reason}")

    if itinerary.fallback_options:
        print("可切换到:")
        for item in itinerary.fallback_options:
            print(f"- {item}")
