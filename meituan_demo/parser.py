from __future__ import annotations

import re
from typing import Any

from .models import Constraint, Goal, SceneType


class GoalParser:
    """使用简单规则把一句自然语言转换为结构化目标。"""

    def parse(self, text: str, context: dict[str, Any] | None = None) -> Goal:
        normalized = text.strip()
        compact = re.sub(r"\s+", "", normalized)
        context = context or {}
        scene = self._detect_scene(compact)
        group_size = self._detect_group_size(compact, scene)
        duration_hours = self._detect_duration(compact)
        time_window = self._detect_time_window(compact)
        distance_preference = self._detect_distance_preference(compact)
        child_age_hint = self._detect_child_age(compact)
        pace_preference = self._detect_pace_preference(compact)
        share_target = self._detect_share_target(scene)
        city = str(context.get("city", "")).strip()
        origin_name = str(context.get("origin_name", "")).strip()
        origin_lat = self._to_float(context.get("origin_lat"))
        origin_lng = self._to_float(context.get("origin_lng"))
        travel_mode = self._detect_travel_mode(context.get("travel_mode"))

        preferences: list[str] = []
        dining_preferences: list[str] = []
        special_needs: list[str] = []

        if scene == "family":
            preferences.extend(["亲子友好", "照顾儿童节奏"])
            special_needs.append("适合儿童")
            if child_age_hint:
                special_needs.append(f"儿童年龄约{child_age_hint}")
        elif scene == "friends":
            preferences.extend(["社交氛围", "方便聊天互动"])
            special_needs.append("适合多人同行")

        if any(token in compact for token in ["吃", "饭", "聚餐", "餐厅"]):
            preferences.append("需要餐饮安排")
        if pace_preference == "轻松":
            preferences.append("少折腾")
        if any(token in compact for token in ["下午茶", "咖啡", "甜品"]):
            preferences.append("适合追加轻量收尾")

        if any(token in compact for token in ["减脂", "清淡", "少油"]):
            dining_preferences.append("清淡饮食")
            special_needs.append("清淡饮食")
        if any(token in compact for token in ["不辣", "微辣"]):
            dining_preferences.append("少辣")
        if "烤肉" in compact:
            dining_preferences.append("烤肉")
        if "火锅" in compact:
            dining_preferences.append("火锅")

        constraints = [
            Constraint(key="scene", value=scene),
            Constraint(key="group_size", value=str(group_size)),
            Constraint(key="duration_hours", value=str(duration_hours)),
            Constraint(key="time_window", value=time_window),
            Constraint(key="distance_preference", value=distance_preference),
            Constraint(key="pace_preference", value=pace_preference),
            Constraint(key="share_target", value=share_target),
            Constraint(key="travel_mode", value=travel_mode),
        ]
        if city:
            constraints.append(Constraint(key="city", value=city))
        if origin_name:
            constraints.append(Constraint(key="origin_name", value=origin_name))
        if origin_lat is not None and origin_lng is not None:
            constraints.append(Constraint(key="origin", value=f"{origin_lng},{origin_lat}"))
        if child_age_hint:
            constraints.append(Constraint(key="child_age_hint", value=child_age_hint))
        if dining_preferences:
            constraints.append(Constraint(key="dining_preferences", value=",".join(self._dedupe(dining_preferences))))

        return Goal(
            raw_text=normalized,
            scene=scene,
            group_size=group_size,
            duration_hours=duration_hours,
            time_window=time_window,
            distance_preference=distance_preference,
            city=city,
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            travel_mode=travel_mode,
            child_age_hint=child_age_hint,
            share_target=share_target,
            pace_preference=pace_preference,
            preferences=self._dedupe(preferences),
            dining_preferences=self._dedupe(dining_preferences),
            special_needs=self._dedupe(special_needs),
            constraints=constraints,
        )

    def _detect_scene(self, text: str) -> SceneType:
        if any(token in text for token in ["老婆", "老公", "孩子", "宝宝", "带娃", "亲子", "家庭", "家人"]):
            return "family"
        if any(token in text for token in ["朋友", "同学", "同事", "闺蜜", "兄弟", "聚会"]) or re.search(
            r"([0-9一二两三四五六七八九十]+)\s*个?人",
            text,
        ):
            return "friends"
        return "generic"

    def _detect_group_size(self, text: str, scene: SceneType) -> int:
        match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?人", text)
        if match:
            return self._parse_number_token(match.group(1))

        # 模式匹配：一家X口  (一家三口/一家四口/一家五口...)
        family_n = re.search(r"一家([0-9一二两三四五六七八九十]+)口", text)
        if family_n:
            return self._parse_number_token(family_n.group(1))

        # 模式匹配：X口之家
        n_family = re.search(r"([0-9一二两三四五六七八九十]+)口之家", text)
        if n_family:
            return self._parse_number_token(n_family.group(1))

        # 夫妻/两口子 = 2
        if re.search(r"(夫妻俩|两口子|两夫妻)", text):
            return 2

        # 两大一小 = 3
        if "两大一小" in text:
            return 3

        if scene == "family":
            return 3
        if scene == "friends":
            return 4
        return 2

    def _detect_duration(self, text: str) -> int:
        range_match = re.search(r"([4-6])\s*[-到~]\s*([4-6])\s*个?小时", text)
        if range_match:
            lower = int(range_match.group(1))
            upper = int(range_match.group(2))
            return (lower + upper) // 2
        match = re.search(r"(\d+)\s*个?小时", text)
        if match:
            hours = int(match.group(1))
            return min(max(hours, 4), 6)
        if "几个小时" in text or "半天" in text:
            return 5
        return 5

    def _detect_time_window(self, text: str) -> str:
        if "上午" in text:
            return "上午"
        if "晚上" in text or "夜" in text:
            return "晚上"
        if "中午" in text:
            return "中午"
        return "下午"

    def _detect_distance_preference(self, text: str) -> str:
        if any(token in text for token in ["别太远", "离家近", "别离家太远", "附近", "就近", "不想跑太远"]):
            return "近场"
        if any(token in text for token in ["远一点也行", "市中心", "开车也行"]):
            return "可稍远"
        return "常规"

    def _detect_travel_mode(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"walking", "walk", "步行"}:
            return "walking"
        return "driving"

    def _detect_child_age(self, text: str) -> str:
        match = re.search(r"(\d+)\s*岁", text)
        if match:
            return f"{match.group(1)}岁"
        if "幼儿" in text or "宝宝" in text:
            return "低龄儿童"
        if "小学生" in text:
            return "学龄儿童"
        return ""

    def _detect_pace_preference(self, text: str) -> str:
        if any(token in text for token in ["不折腾", "别太折腾", "轻松", "悠闲", "别太赶"]):
            return "轻松"
        if any(token in text for token in ["紧凑", "多安排点", "尽量丰富"]):
            return "紧凑"
        return "常规"

    def _detect_share_target(self, scene: SceneType) -> str:
        if scene == "family":
            return "家人"
        if scene == "friends":
            return "朋友"
        return "同行人"

    def _parse_number_token(self, token: str) -> int:
        if token.isdigit():
            return int(token)
        mapping = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        if token in mapping:
            return mapping[token]
        if len(token) == 2 and token.startswith("十") and token[1] in mapping:
            return 10 + mapping[token[1]]
        return 2

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value not in result:
                result.append(value)
        return result

    def _to_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
