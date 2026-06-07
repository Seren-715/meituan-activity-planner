from __future__ import annotations

from .models import Goal, Itinerary


class ShareComposer:
    def compose(self, goal: Goal, itinerary: Itinerary, execution_summary: list[str] | None = None) -> str:
        stop_text = "，随后去".join(
            f"{stop.start_time} {stop.title} ({stop.duration_minutes} 分钟)" for stop in itinerary.stops
        )
        summary_text = ""
        if execution_summary:
            summary_text = " 已完成的关键动作包括：" + "；".join(execution_summary) + "。"
        if goal.scene == "family":
            opener = "家人版安排已确认"
            tone = f"这版会更照顾孩子节奏，整体按{goal.distance_preference}路线来走。"
        elif goal.scene == "friends":
            opener = "朋友局安排已确认"
            tone = f"这版更适合边玩边聊，整体按{goal.distance_preference}路线串起来。"
        else:
            opener = "下午安排已确认"
            tone = f"整体按{goal.distance_preference}路线推进，尽量把时间和通勤压顺。"
        return (
            f"{opener}：{goal.time_window}从{goal.origin_name or '当前位置'}出发，先去{stop_text}。"
            f"预计总时长约 {itinerary.total_minutes} 分钟，其中通勤约 {itinerary.total_travel_minutes} 分钟。"
            f"{tone}{summary_text}"
        )
