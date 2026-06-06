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
        opener = "家人版安排已确认" if goal.scene == "family" else "朋友局安排已确认" if goal.scene == "friends" else "下午安排已确认"
        return (
            f"{opener}：{goal.time_window}从{goal.origin_name or '当前位置'}出发，先去{stop_text}。"
            f"预计总时长约 {itinerary.total_minutes} 分钟，其中通勤约 {itinerary.total_travel_minutes} 分钟，"
            f"整体以{goal.distance_preference}路线为主。"
            f"{summary_text}"
        )
