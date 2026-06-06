from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ConversationSlots:
    # 统一保存对话中逐步抽取出的关键信息，供追问与规划复用。
    goal: str = ""
    scene: str = ""
    group_size: str = ""
    city: str = ""
    time_window: str = ""
    duration_hours: str = ""
    distance_preference: str = ""
    travel_mode: str = ""
    child_age_hint: str = ""
    dining_preference: str = ""
    pace_preference: str = ""
    special_needs: str = ""


class ConversationOrchestrator:
    def reply(self, messages: list[dict[str, str]]) -> dict[str, object]:
        # 基于完整对话历史抽取槽位，只对最新一句决定当前回复口吻。
        user_messages = [
            str(item.get("content", "")).strip()
            for item in messages
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ]
        latest_user = user_messages[-1] if user_messages else ""
        # 仅让真正携带需求的信息进入槽位抽取，避免“你好/谢谢”污染 goal。
        joined = " ".join(item for item in user_messages if self._has_meaningful_intent(item))
        slots = self._extract_slots(joined)
        next_field = self._next_missing_field(slots)

        invalid_input = self._classify_invalid_input(latest_user)
        smalltalk = self._classify_smalltalk(latest_user)
        if invalid_input:
            assistant_reply = self._reply_to_invalid(slots, next_field)
        elif smalltalk and not self._has_meaningful_intent(latest_user):
            assistant_reply = self._reply_to_smalltalk(smalltalk, slots)
        else:
            if next_field is None:
                assistant_reply = "好，我大概已经抓到重点了。我可以开始帮你安排一版更具体的本地方案。"
            else:
                assistant_reply = self._build_follow_up(latest_user, slots, next_field)

        ready = next_field is None
        return {
            "assistant_reply": assistant_reply,
            "slots": asdict(slots),
            "ready_to_plan": ready,
            "suggested_replies": self._suggestions_for(slots, next_field),
            "plan_text": self._build_plan_text(slots),
        }

    def _classify_smalltalk(self, text: str) -> str | None:
        normalized = re.sub(r"\s+", "", text).lower()
        if re.fullmatch(r"(hi|hello|hey|你好|您好|哈喽|嗨|在吗|在嘛|有人吗)[!?？。]*", normalized):
            return "greeting"
        if re.search(r"(你是谁|你是干嘛的|你能做什么|你会什么|这是啥|这是什么意思)", normalized):
            return "identity"
        if re.fullmatch(r"(额+|嗯+|呃+|哦+|啊+|诶+|随便|不知道|不清楚|没想好)", normalized):
            return "filler"
        if re.search(r"(谢谢|多谢|辛苦了|谢啦)", normalized):
            return "thanks"
        return None

    def _has_meaningful_intent(self, text: str) -> bool:
        return any(
            token in text
            for token in [
                "想",
                "去",
                "玩",
                "吃",
                "安排",
                "下午",
                "晚上",
                "上午",
                "老婆",
                "孩子",
                "朋友",
                "聚会",
                "小时",
                "附近",
                "餐厅",
            ]
        )

    def _classify_invalid_input(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return "empty"

        # 纯标点、符号或分隔符不算有效输入，避免触发重复追问。
        semantic = re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)
        if not semantic:
            return "symbols"
        return None

    def _extract_slots(self, text: str) -> ConversationSlots:
        # 把多轮用户输入合并后做一次轻量规则抽取，避免前端自己维护填表状态。
        compact = re.sub(r"\s+", "", text)
        slots = ConversationSlots()
        if compact:
            slots.goal = text.strip()

        if any(token in compact for token in ["老婆", "老公", "孩子", "宝宝", "带娃", "亲子", "家庭", "家人"]):
            slots.scene = "family"
        elif any(token in compact for token in ["朋友", "同学", "同事", "闺蜜", "兄弟", "聚会"]):
            slots.scene = "friends"
        elif compact:
            slots.scene = "generic"

        group_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?人", compact)
        if group_match:
            slots.group_size = str(self._parse_number(group_match.group(1)))
        elif "两大一小" in compact or "一家三口" in compact:
            slots.group_size = "3"
        elif slots.scene == "family":
            slots.group_size = "3"
        elif slots.scene == "friends":
            friend_count = re.search(r"([0-9])男([0-9])女", compact)
            if friend_count:
                slots.group_size = str(int(friend_count.group(1)) + int(friend_count.group(2)))
            else:
                slots.group_size = "4"

        city_match = re.search(
            r"(北京|上海|广州|深圳|杭州|苏州|南京|成都|重庆|天津|武汉|西安|长沙|福州|厦门|泉州|宁波|青岛|郑州|合肥|无锡|常州|南昌|昆明|大连|沈阳|长春|哈尔滨|佛山|东莞)(?:市)?",
            text,
        )
        if city_match:
            slots.city = city_match.group(1)
        else:
            suffix_match = re.search(r"([A-Za-z\u4e00-\u9fa5]{2,8}(?:市|区|县))", text)
            if suffix_match and not re.search(r"(小时|孩子|老婆|朋友|活动|安排)", suffix_match.group(1)):
                slots.city = suffix_match.group(1)

        if "上午" in compact or "早上" in compact:
            slots.time_window = "上午"
        elif "中午" in compact:
            slots.time_window = "中午"
        elif "晚上" in compact or "今晚" in compact or "夜" in compact:
            slots.time_window = "晚上"
        elif "下午" in compact:
            slots.time_window = "下午"

        duration_match = re.search(r"(\d+)\s*个?\s*小时", compact)
        if duration_match:
            slots.duration_hours = duration_match.group(1)
        elif "几个小时" in compact or "半天" in compact:
            slots.duration_hours = "5"

        if any(token in compact for token in ["别太远", "离家近", "别离家太远", "附近", "就近", "不想跑太远"]):
            slots.distance_preference = "近场"
        elif any(token in compact for token in ["远一点也行", "稍远也行", "开车也行"]):
            slots.distance_preference = "可稍远"

        if any(token in compact for token in ["步行", "走路"]):
            slots.travel_mode = "walking"
        elif any(token in compact for token in ["开车", "打车", "驾车", "自驾"]):
            slots.travel_mode = "driving"

        age_match = re.search(r"(\d+)\s*岁", compact)
        if age_match:
            slots.child_age_hint = f"{age_match.group(1)}岁"

        dining_match = re.search(r"(清淡减脂|清淡|减脂|火锅烧烤|火锅|烧烤|家常菜|家常|粤菜|川菜|小吃|日料|西餐)", text)
        if dining_match:
            slots.dining_preference = dining_match.group(1)
        elif "吃饭" in compact or "餐厅" in compact:
            slots.dining_preference = "需要餐饮安排"

        if any(token in compact for token in ["轻松", "不折腾", "悠闲", "松弛"]):
            slots.pace_preference = "轻松"
        elif any(token in compact for token in ["丰富", "紧凑", "多安排点"]):
            slots.pace_preference = "紧凑"

        special_hits = []
        for token in ["停车方便", "安静一点", "避开太吵", "别太吵", "室内", "下雨也行", "带老人", "无障碍"]:
            if token in text:
                special_hits.append(token)
        if special_hits:
            slots.special_needs = "、".join(special_hits)

        return slots

    def _parse_number(self, token: str) -> int:
        if token.isdigit():
            return int(token)
        mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        return mapping.get(token, 2)

    def _next_missing_field(self, slots: ConversationSlots) -> str | None:
        # 追问顺序尽量贴近自然聊天，优先补齐决定路线质量的核心信息。
        priorities = [
            "goal",
            "scene",
            "city",
            "time_window",
            "duration_hours",
            "distance_preference",
        ]
        if slots.scene == "family":
            priorities.append("child_age_hint")
        priorities.extend(["dining_preference", "pace_preference"])
        for field in priorities:
            if not getattr(slots, field):
                return field
        return None

    def _build_follow_up(self, latest_user: str, slots: ConversationSlots, next_field: str) -> str:
        ack = self._acknowledge(latest_user, slots)
        prompts = {
            "goal": "你可以直接跟我说说，今天更想怎么玩，或者想吃点什么。",
            "scene": "这次主要是和谁一起出门？我会按场景来挑活动和餐厅。",
            "city": "你现在在哪个城市？我先把范围卡住，后面路线会更靠谱。",
            "time_window": "你大概想什么时候出发，上午、下午还是晚上？",
            "duration_hours": "这次大概想安排多久？4 到 6 个小时我都可以帮你排。",
            "distance_preference": "你对距离有没有要求？比如近一点、别太远，或者稍微远点也能接受。",
            "child_age_hint": "如果会带小朋友，孩子大概多大呀？我想把活动选得更贴一点。",
            "dining_preference": "吃的方面有什么偏好吗？比如清淡一点、减脂、家常菜，或者热闹一点都行。",
            "pace_preference": "整体你更想轻松一点，还是内容丰富一点？",
        }
        return f"{ack}{prompts[next_field]}"

    def _acknowledge(self, latest_user: str, slots: ConversationSlots) -> str:
        if slots.scene == "family" and ("老婆" in latest_user or "孩子" in latest_user or "家人" in latest_user):
            return "好呀，家庭出门我先帮你往轻松、顺路、适合一起待着的方向想。"
        if slots.scene == "friends" and ("朋友" in latest_user or "聚会" in latest_user):
            return "明白，你这是偏朋友聚会的场景，我会优先考虑聊天方便、氛围不错的组合。"
        if slots.time_window or slots.duration_hours or slots.distance_preference:
            return "收到，这样时间和距离的大方向我就有数了。"
        return "明白，我先顺着你的想法往下捋一捋。"

    def _reply_to_smalltalk(self, kind: str, slots: ConversationSlots) -> str:
        if kind == "identity":
            return "我是帮你安排本地活动的。你可以直接告诉我，今天想和谁出去、想玩多久，或者想吃点什么。"
        if kind == "thanks":
            return "不客气，你继续说就行，我接着帮你捋。"
        if kind == "filler":
            return "没事，你先随便说一点想法也行，比如和谁一起、想玩多久，我来帮你补全。"
        if slots.goal:
            return "我在，你可以继续补充，我会边听边帮你整理。"
        return "我在呀。你直接告诉我，今天想做点什么就行。"

    def _reply_to_invalid(self, slots: ConversationSlots, next_field: str | None) -> str:
        prompts = {
            "goal": "你可以直接告诉我，今天想和谁出门、想玩多久，或者想吃点什么。",
            "scene": "你可以直接说，这次是和家人、朋友，还是自己出门。",
            "city": "你可以直接告诉我你现在在哪个城市。",
            "time_window": "你可以直接说想上午、下午还是晚上出发。",
            "duration_hours": "你可以直接说大概玩 4 小时、5 小时或者 6 小时。",
            "distance_preference": "你可以直接说想近一点，还是稍微远一点也能接受。",
            "child_age_hint": "如果会带小朋友，可以直接告诉我孩子大概几岁。",
            "dining_preference": "你可以直接说想吃清淡一点、家常菜，还是没特别要求。",
            "pace_preference": "你可以直接说想轻松一点，还是内容丰富一点。",
        }
        if next_field is None:
            return "这句我没太看懂。你要是还想补充细节，可以直接说时间、距离或者吃饭偏好。"
        return f"这句我没太看懂。{prompts[next_field]}"

    def _suggestions_for(self, slots: ConversationSlots, next_field: str | None) -> list[str]:
        if next_field == "goal":
            return [
                "今天下午想和老婆孩子出去玩几个小时，别离家太远",
                "晚上想和朋友聚个会，先玩再吃饭",
                "周末想一个人随便逛逛放松一下",
            ]
        if next_field == "scene":
            return ["和家人一起", "和朋友一起", "我自己出去"]
        if next_field == "city":
            return ["我在福州", "上海", "杭州"]
        if next_field == "time_window":
            return ["下午出发", "晚上出发", "上午出发"]
        if next_field == "duration_hours":
            return ["4小时左右", "5小时左右", "6小时左右"]
        if next_field == "distance_preference":
            return ["别太远", "近一点最好", "稍远也可以"]
        if next_field == "child_age_hint":
            return ["3岁", "5岁", "8岁"]
        if next_field == "dining_preference":
            return ["清淡减脂", "家常菜就行", "没特别要求"]
        if next_field == "pace_preference":
            return ["轻松一点", "丰富一点", "常规就行"]
        if next_field is None:
            return ["开始生成方案", "再补充一点细节"]
        return []

    def _build_plan_text(self, slots: ConversationSlots) -> str:
        # 把已确认信息重新组织成一段更适合送入规划器的自然语言描述。
        parts: list[str] = []
        if slots.goal:
            parts.append(slots.goal)
        if slots.city and slots.city not in slots.goal:
            parts.append(f"当前城市是{slots.city}")
        if slots.child_age_hint and slots.child_age_hint not in slots.goal:
            parts.append(f"孩子大概{slots.child_age_hint}")
        if slots.dining_preference and slots.dining_preference not in slots.goal:
            parts.append(f"饮食偏好是{slots.dining_preference}")
        if slots.pace_preference and slots.pace_preference not in slots.goal:
            parts.append(f"整体节奏偏{slots.pace_preference}")
        if slots.special_needs and slots.special_needs not in slots.goal:
            parts.append(f"还需要注意{slots.special_needs}")
        return "，".join(parts)
