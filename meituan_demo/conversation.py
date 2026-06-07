from __future__ import annotations

import re
import random
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
        """状态机驱动的对话回复。

        处理优先级：
        1. 无效输入 / 寒暄（保持不变）
        2. 改口检测 —— 前后槽位变化 → 确认改口
        3. 冲突检测 —— 语义矛盾 → 提示冲突
        4. 准备就绪 → 复述确认
        5. 正常追问
        """
        user_messages = [
            str(item.get("content", "")).strip()
            for item in messages
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ]
        latest_user = user_messages[-1] if user_messages else ""

        # --- 无效输入 / 寒暄优先处理 ---
        invalid_input = self._classify_invalid_input(latest_user)
        smalltalk = self._classify_smalltalk(latest_user)

        # 构建全量槽位
        joined = " ".join(item for item in user_messages if self._has_meaningful_intent(item))
        slots = self._extract_slots(joined)
        next_field = self._next_missing_field(slots)

        if invalid_input:
            assistant_reply = self._reply_to_invalid(slots, next_field)
            ready = False
        elif smalltalk and not self._has_meaningful_intent(latest_user):
            assistant_reply = self._reply_to_smalltalk(smalltalk, slots)
            ready = False
        else:
            # --- 改口检测：比较不含最新消息的槽位 vs 全量槽位 ---
            prev_joined = " ".join(item for item in user_messages[:-1] if self._has_meaningful_intent(item))
            prev_slots = self._extract_slots(prev_joined) if prev_joined else ConversationSlots()
            changes = self._detect_slot_changes(prev_slots, slots, latest_user)

            if changes:
                # 有改口 -> 确认改动 + 继续追问
                ack = self._build_change_ack(changes, slots)
                # 同时检查冲突
                conflict_info = self._detect_conflicts(slots)
                if conflict_info:
                    ack += "\n\n" + conflict_info
                if next_field is None:
                    assistant_reply = ack + " " + self._build_recap(slots)
                    ready = True
                else:
                    follow = self._build_follow_up(latest_user, slots, next_field)
                    prompt_part = follow.split("。", 1)[-1].strip() if "。" in follow else follow
                    assistant_reply = ack + " " + prompt_part
                    ready = False
            elif self._detect_conflicts(slots):
                # 有冲突 -> 提示冲突
                conflict_text = self._detect_conflicts(slots)
                assistant_reply = conflict_text
                ready = False
            elif next_field is None:
                # 一切就绪 -> 复述确认
                assistant_reply = self._build_recap(slots) + " 没问题的话我就帮你出方案啦～"
                ready = True
            else:
                # 正常追问
                assistant_reply = self._build_follow_up(latest_user, slots, next_field)
                ready = False

        goal = self._build_goal(slots) if ready else None
        if ready and goal is None:
            # 兜底保护：一旦 Goal 组装失败，就回到继续澄清，避免前端进入半完成状态。
            ready = False
            assistant_reply = "我先把你的需求再确认严一点，避免直接给你出错方案。你再补一句，我就继续往下排。"
        return {
            "assistant_reply": assistant_reply,
            "slots": asdict(slots),
            "ready_to_plan": ready,
            "suggested_replies": self._suggestions_for(slots, next_field),
            "plan_text": self._build_plan_text(slots),
            "goal": goal,
        }

    # --- 状态机核心方法 ------------------------------------

    _SLOT_LABELS: dict[str, str] = {
        "goal": "目标",
        "scene": "出行场景",
        "group_size": "人数",
        "city": "城市",
        "time_window": "时间窗口",
        "duration_hours": "时长",
        "distance_preference": "距离偏好",
        "child_age_hint": "孩子年龄",
        "dining_preference": "饮食偏好",
        "pace_preference": "节奏偏好",
    }

    _CHANGE_DOMAIN_KEYWORDS: dict[str, list[str]] = {
        "time_window": ["上午", "中午", "下午", "晚上", "早上", "今晚", "夜"],
        "duration_hours": ["小时", "钟头", "点"],
        "distance_preference": ["近", "远", "附近", "周边", "开车"],
        "scene": ["老婆", "老公", "孩子", "朋友", "同事", "闺蜜", "家人", "自己"],
        "group_size": ["人", "个", "位"],
        "city": ["北京", "上海", "广州", "深圳", "杭州", "苏州", "南京", "成都", "重庆", "福州", "厦门", "泉州"],
        "child_age_hint": ["岁", "年龄", "多大"],
        "dining_preference": ["吃", "饭", "餐", "火锅", "烧烤", "清淡", "家常", "粤菜", "川菜"],
        "pace_preference": ["轻松", "紧凑", "丰富", "悠闲", "折腾", "安排", "松", "紧"],
    }

    def _detect_slot_changes(
        self,
        prev_slots: ConversationSlots,
        curr_slots: ConversationSlots,
        latest_user: str,
    ) -> dict[str, tuple[str, str]]:
        """检测槽位变化：返回 {field: (old_value, new_value)}。"""
        fields = [
            "scene", "group_size", "city", "time_window",
            "duration_hours", "distance_preference", "child_age_hint",
            "dining_preference", "pace_preference",
        ]
        changes: dict[str, tuple[str, str]] = {}
        for f in fields:
            old_val = getattr(prev_slots, f, "")
            new_val = getattr(curr_slots, f, "")
            if not old_val or not new_val:
                continue
            if old_val == new_val:
                continue
            # 确认最新消息确实涉及该字段的领域关键词
            domain_kw = self._CHANGE_DOMAIN_KEYWORDS.get(f, [])
            if domain_kw and not any(kw in latest_user for kw in domain_kw):
                continue
            changes[f] = (old_val, new_val)
        return changes

    def _build_change_ack(self, changes: dict[str, tuple[str, str]], slots: ConversationSlots) -> str:
        """生成改口确认文本。"""
        parts: list[str] = []
        for field_name, (old_val, new_val) in changes.items():
            label = self._SLOT_LABELS.get(field_name, field_name)
            parts.append(f"{label}从「{old_val}」改成「{new_val}」了")
        if not parts:
            return "好的，记下了。"
        body = "，".join(parts)
        starts = [
            f"好的，{body}，我更新一下。",
            f"收到，{body}，已经记下来了。",
            f"明白，{body}。",
        ]
        return random.choice(starts)

    def _detect_conflicts(self, slots: ConversationSlots) -> str | None:
        conflicts: list[str] = []

        if slots.time_window == "晚上" and slots.duration_hours.isdigit() and int(slots.duration_hours) >= 5:
            conflicts.append("晚上出门玩五个小时以上可能会到很晚哦，确定这样可以吗？")

        if slots.scene == "family" and slots.pace_preference == "紧凑":
            conflicts.append("带孩子的话节奏排太满可能会比较累，要不要改成轻松一点的？")

        if slots.distance_preference == "近场" and slots.group_size.isdigit() and int(slots.group_size) >= 5:
            conflicts.append("选了就近，不过5个人以上的话出发点附近可能不太好找位置，要不要放宽一点距离？")

        if slots.scene == "family" and slots.child_age_hint:
            age_num = self._parse_age(slots.child_age_hint)
            if age_num is not None and age_num <= 6:
                hot_kw = ["火锅", "烧烤", "烤"]
                if slots.dining_preference and any(kw in slots.dining_preference for kw in hot_kw):
                    conflicts.append("孩子还小的话，火锅烧烤要注意安全哦，要不要我帮你换一家更亲子的餐厅？")

        if slots.travel_mode == "walking" and slots.distance_preference == "可稍远":
            conflicts.append("选了步行但距离偏好是「可稍远」——走路可能只能覆盖附近哦，要不要改成开车？")

        if not conflicts:
            return None
        return "对了，有几个地方提醒你一下：\n" + "\n".join(f"  · {c}" for c in conflicts)

    def _parse_age(self, age_hint: str) -> int | None:
        """从年龄提示中提取数字。"""
        if not age_hint:
            return None
        m = re.search(r"\d+", str(age_hint))
        return int(m.group()) if m else None

    def _build_recap(self, slots: ConversationSlots) -> str:
        clauses: list[str] = []

        if slots.city:
            clauses.append(f"在{slots.city}")

        time_scene = []
        if slots.time_window:
            time_scene.append(slots.time_window)
        if slots.scene == "family":
            time_scene.append("带家人")
        elif slots.scene == "friends":
            time_scene.append("跟朋友")
        if slots.group_size:
            time_scene.append(f"{slots.group_size}个人")
        if time_scene:
            clauses.append("，".join(time_scene))

        if slots.child_age_hint:
            clauses.append(f"孩子差不多{slots.child_age_hint}")

        if slots.duration_hours:
            clauses.append(f"玩{slots.duration_hours}个小时左右")

        if slots.distance_preference == "近场":
            clauses.append("不想跑太远")
        elif slots.distance_preference == "可稍远":
            clauses.append("稍微远点也能接受")

        if slots.dining_preference and slots.dining_preference != "需要餐饮安排":
            clauses.append(f"想吃{slots.dining_preference}")

        if slots.pace_preference == "轻松":
            clauses.append("节奏轻松一点")
        elif slots.pace_preference == "紧凑":
            clauses.append("内容排满一点")

        if not clauses:
            return "信息还不够完整，再跟我说说你的想法？"

        body = "，".join(clauses)
        return f"我帮你理一下哈——{body}。我理解的对吗？"

    def _classify_smalltalk(self, text: str) -> str | None:
        """识别寒暄、身份询问、填词、感谢、困惑等非需求型对话。"""
        normalized = text.strip()
        compact = re.sub(r"\s+", "", normalized).lower()
        if re.fullmatch(
            r"(h+i+|he+y+|yo+|halo|hola|hi[!?]*|hello[!?]*|"
            r"你好|您好|你好呀|您好呀|嗨|哈喽|哈罗|"
            r"在吗|在嘛|在不在|在么|有人吗|有人在吗|有人不|"
            r"喂|你好在吗|哈罗在吗|"
            r"嗯[?？]?|额[?？]?|啊[?？]?)[!?？！。]*",
            compact,
        ):
            return "greeting"
        if re.search(
            r"(你是谁|你是干嘛的|你能做什么|你会什么|你会干吗|"
            r"这是啥|这是什么意思|你有什么用|你叫什么|叫什么名字|"
            r"你是什么|你是机器人吗|你是AI吗|你是人吗|"
            r"你能帮我做什么|你能帮我干嘛)",
            compact,
        ):
            return "identity"
        if re.search(
            r"(谢谢|多谢|辛苦了|谢啦|感谢|谢谢你|谢谢啦|多谢啦|"
            r"万分感谢|真的谢谢|太感谢了|好的谢谢|好谢谢)",
            compact,
        ):
            return "thanks"
        if re.fullmatch(r"[\?？]+", compact):
            return "confused"
        if re.fullmatch(r"[.。…]+", compact):
            return "filler"
        if re.fullmatch(
            r"(额|嗯|诶|哦|啊|啧|呃|哈|嘿|哼|哟|"
            r"随便|不知道|不懂|不清楚|没想好|没有想法|无所谓|都行|随便吧|"
            r"你说呢|你觉得呢|我也不知道|我不懂|不清楚呢|"
            r"好|好的|行|可以|ok|okk)",
            compact,
        ):
            return "filler"
        if len(compact) <= 1:
            return "filler"
        if re.fullmatch(r"\d+", compact):
            return "filler"
        if re.fullmatch(r"(test|testing|testt|abc|asdf|qwer|123|testing123)", compact):
            return "filler"
        return None

    def _has_meaningful_intent(self, text: str) -> bool:
        """判断文本是否携带活动规划的意图信息。"""
        return any(
            token in text
            for token in [
                "想",
                "去",
                "玩",
                "吃",
                "安排",
                "规划",
                "推荐",
                "建议",
                "帮我",
                "帮忙",
                "下午",
                "晚上",
                "上午",
                "周末",
                "今天",
                "明天",
                "老婆",
                "孩子",
                "带娃",
                "宝宝",
                "爸妈",
                "父母",
                "老人",
                "朋友",
                "闺蜜",
                "兄弟",
                "同事",
                "同学",
                "聚会",
                "聚餐",
                "约饭",
                "逛街",
                "看电影",
                "逛",
                "遛",
                "小时",
                "分钟",
                "附近",
                "周边",
                "餐厅",
                "吃饭",
                "火锅",
                "烧烤",
                "咖啡",
                "甜品",
                "下午茶",
                "户外",
                "室内",
                "公园",
                "商场",
                "商圈",
                "打卡",
                "拍照",
                "接送",
                "散步",
                "自驾",
                "打车",
                "步行",
            ]
        )

    def _classify_invalid_input(self, text: str) -> str | None:
        """识别完全无意义输入：空文本或纯符号。
        注意：? 。。等现在走 _classify_smalltalk，这里只保留真正空/纯不可见符号。
        """
        normalized = text.strip()
        if not normalized:
            return "empty"
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

        if any(token in compact for token in ["老婆", "老公", "孩子", "宝宝", "带娃", "亲子", "家庭", "家人"]) or re.search(r"(带.*孩子|陪.*老婆|陪.*老公)", compact):
            slots.scene = "family"
        elif any(token in compact for token in ["朋友", "同学", "同事", "闺蜜", "兄弟", "聚会"]) or re.search(r"(约了.*人|叫上.*人)", compact):
            slots.scene = "friends"
        elif compact:
            slots.scene = "generic"

        group_match = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?人", compact)
        if group_match:
            slots.group_size = str(self._parse_number(group_match.group(1)))
        # 模式匹配：一家X口 / X口之家
        family_n = re.search(r"一家([0-9一二两三四五六七八九]+)口", compact)
        if family_n:
            slots.group_size = str(self._parse_number(family_n.group(1)))
        elif re.search(r"([0-9一二两三四五六七八九]+)口之家", compact):
            n_family = re.search(r"([0-9一二两三四五六七八九]+)口之家", compact)
            slots.group_size = str(self._parse_number(n_family.group(1)))
        elif re.search(r"(夫妻俩|两口子|两夫妻)", compact):
            slots.group_size = "2"
        elif "两大一小" in compact:
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
        # 模式匹配：在X（2-4字中文城市名），不限已知城市列表
        if not slots.city:
            in_city = re.search(r"在([\u4e00-\u9fa5]{2,4})(?:市|区|县|(?=[，。\s\n]|$))", text)
            if in_city:
                slots.city = in_city.group(1)

        if any(t in compact for t in ["上午", "早上", "早晨", "一大早", "早起"]):
            slots.time_window = "上午"
        elif "中午" in compact:
            slots.time_window = "中午"
        elif any(t in compact for t in ["晚上", "今晚", "夜里", "夜间", "傍晚", "黄昏", "晚饭后"]):
            slots.time_window = "晚上"
        elif "下午" in compact:
            slots.time_window = "下午"

        duration_match = re.search(r"(\d+)\s*个?\s*小时", compact)
        if duration_match:
            slots.duration_hours = duration_match.group(1)
        elif "几个小时" in compact or "半天" in compact:
            slots.duration_hours = "5"

        if re.search(r"(不想.*远|近一?点|附近|就近|别.*远|离家近|不.*跑.*远)", compact):
            slots.distance_preference = "近场"
        elif re.search(r"(远.*也行|多远都行|稍.*远|开车也行|远点.*行)", compact):
            slots.distance_preference = "可稍远"

        if re.search(r"(步行|走路|散步)", compact):
            slots.travel_mode = "walking"
        elif re.search(r"(开车|打车|驾车|自驾|坐车)", compact):
            slots.travel_mode = "driving"

        age_match = re.search(r"(\d+)\s*岁", compact)
        if age_match:
            slots.child_age_hint = f"{age_match.group(1)}岁"

        dining_match = re.search(r"(清淡减脂|清淡|减脂|火锅烧烤|火锅|烧烤|家常菜|家常|粤菜|川菜|小吃|日料|西餐)", text)
        if dining_match:
            slots.dining_preference = dining_match.group(1)
        elif "吃饭" in compact or "餐厅" in compact:
            slots.dining_preference = "需要餐饮安排"

        if re.search(r"(轻松|不折腾|悠闲|松弛|慢慢逛|随便逛)", compact):
            slots.pace_preference = "轻松"
        elif re.search(r"(紧凑|丰富|多.*排|排.*满|满.*点)", compact):
            slots.pace_preference = "紧凑"

        special_hits = []
        special_rules = [
            ("停车方便", r"停车|车位"),
            ("安静一点", r"安静|不.*吵|别.*吵|避开.*吵"),
            ("室内优先", r"室内|不淋雨|遮阳"),
            ("不怕下雨", r"下雨.*行|不怕.*雨|下雨.*没事"),
            ("带老人", r"老人|爸妈|父母|长辈|爷|奶"),
            ("无障碍", r"无障碍|轮椅|行动不便"),
            ("宠物友好", r"宠物|狗|猫|带狗|带猫"),
            ("拍照出片", r"拍照|出片|打卡|好看"),
        ]
        for label, pattern in special_rules:
            if re.search(pattern, text):
                special_hits.append(label)
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
            "goal": "跟我说说，今天想怎么玩？或者想吃什么？",
            "scene": "这次打算跟谁一起出门呀？跟家人、朋友还是自己逛？",
            "city": "你们现在在哪个城市，或者准备从哪个商圈附近出发呢？我先圈个出发范围，后面路线会更靠谱。",
            "time_window": "想什么时候出发？上午、下午还是晚上？",
            "duration_hours": "大概想玩多久？4到6个小时我都能帮你排。",
            "distance_preference": "距离上有要求吗？想近一点，还是稍微远点也没关系？",
            "child_age_hint": "会带小朋友吗？孩子大概多大？我想帮你们挑更合适的活动。",
            "dining_preference": "吃东西方面有偏好吗？清淡一点、家常菜，还是热闹一点都行。",
            "pace_preference": "整体想轻松一点，还是排满一点更过瘾？",
        }
        return f"{ack}{prompts[next_field]}"

    def _acknowledge(self, latest_user: str, slots: ConversationSlots) -> str:
        """根据已有槽位返回自然的承接语。"""
        if slots.scene == "family" and ("老婆" in latest_user or "孩子" in latest_user or "家人" in latest_user):
            return "好的～家庭出门的话，我帮你往轻松、顺路、适合一起待着的方向想。"
        if slots.scene == "friends" and ("朋友" in latest_user or "聚会" in latest_user):
            return "明白，朋友聚会嘛，我会优先找那种聊天方便、氛围好的组合。"
        if slots.time_window or slots.duration_hours or slots.distance_preference:
            return "收到，时间和距离的大方向有数了。"
        return "明白，我顺着你的想法往下缕一下。"

    def _reply_to_smalltalk(self, kind: str, slots: ConversationSlots) -> str:
        """小闲聊回复：友好回应后自然引导回活动规划。"""
        if kind == "greeting":
            reply = random.choice(self._GREETING_REPLIES)
            if slots.goal:
                reply += " 你之前说的我还记着呢，可以继续补充。"
            return reply

        if kind == "identity":
            return self._IDENTITY_REPLY

        if kind == "thanks":
            reply = random.choice(self._THANKS_REPLIES)
            if slots.goal:
                reply += " 你之前提到的我已经记下了，继续说的话我接着完善。"
            return reply

        if kind == "confused":
            return (
                "是不是还不知道怎么说？没关系的～直接告诉我你想干什么就行，"
                "比如「今天下午想带孩子出去玩几个小时」或者「晚上跟朋友聚个餐」，不用很精确的。"
            )

        if kind == "filler":
            return random.choice(self._FILLER_REPLIES)

        # fallback
        if slots.goal:
            return "我在，你可以继续补充，我会边听边帮你整理。"
        return "我在呢。你直接告诉我今天想做什么就行。"

    _INVALID_REPLIES: list[str] = [
        "这个我没太看懂，不过你可以直接告诉我想和谁出门、想玩多久，或者想吃什么，我都可以帮你安排。",
        "其实你随便说点想法就行，比如「下午想和闺蜜去逛逛」「晚上带孩子附近转转」，我先帮你缕一道。",
        "这句话信息量少了一点，没关系——你直接说场景我来补细节，比如先说和谁一起、大概多久。",
    ]

    _GREETING_REPLIES: list[str] = [
        "你好呀！今天想出门做点什么吗？比如和谁一起、想玩多久，随便说说我就帮你安排。",
        "嗨！我在这儿呢。你直接说想怎么安排今天的行程就好，我边听边整理。",
        "哈喽！直接告诉我想和谁出去、想干什么，我就可以帮你拟方案了。",
    ]

    _FILLER_REPLIES: list[str] = [
        "没事，你先随便说个大概想法也行。比如今天想和谁出门、想去哪一片、大概多长时间，剩下的我来补。",
        "看起来你还没想好呀，没关系——你可以先说一个小方向，比如「带孩子去公园转转」或者「跟朋友聚个餐」，我帮你展开。",
        "不着急，慢慢来。你可以先告诉我：是家庭出行还是朋友聚会？大概想玩几个小时？我顺着往下帮你缕。",
    ]

    _THANKS_REPLIES: list[str] = [
        "不客气，你继续补充就行，我边听边帮你整理。",
        "客气啦，直接告诉我更多细节，我接着帮你缕方案。",
        "应该的～还有什么想法可以继续跟我说。",
    ]

    _IDENTITY_REPLY: str = (
        "我是帮你安排本地活动的～你直接跟我说想法就行，"
        "比如想和谁出去、去哪、玩多久，我就能给你出一版完整的方案。"
    )

    def _reply_to_invalid(self, slots: ConversationSlots, next_field: str | None) -> str:
        """无效输入回复：根据缺失字段给出更有温度的引导。"""
        prompts = {
            "goal": "直接跟我说就行，比如想和谁一起、想去哪、玩多久。",
            "scene": "直接说吧，是带家人、约朋友还是自己出门转转？",
            "city": "你现在在哪个城市，或者从哪一片出发呀？告诉我一下就好。",
            "time_window": "想上午、下午还是晚上出发？",
            "duration_hours": "大概玩多久？4小时、5小时还是6小时？",
            "distance_preference": "想近一点，还是稍微远点也能接受？",
            "child_age_hint": "会带小朋友的话，孩子几岁了？我帮你挑更合适的活动。",
            "dining_preference": "想吃什么？清淡一点、家常菜，还是没特别要求？",
            "pace_preference": "想轻松一点，还是排满一点？",
        }

        if next_field is None:
            return random.choice(self._INVALID_REPLIES) + " 当然，如果你觉得差不多了，也可以让我直接开始规划。"

        lead = prompts.get(next_field, random.choice(self._INVALID_REPLIES))
        return f"{random.choice(self._INVALID_REPLIES)} {lead}"

    def _suggestions_for(self, slots: ConversationSlots, next_field: str | None) -> list[str]:
        if next_field == "goal":
            return [
                "今天下午想和老婆孩子从公司附近出发玩几个小时，别太远",
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
            return ["确认无误，开始规划", "再改一点"]
        return []


    def _build_goal(self, slots: ConversationSlots) -> dict[str, object]:
        """直接将 ConversationSlots 构建为结构化 Goal dict，跳过 plan_text 文本往返。"""
        if not self._is_goal_ready(slots):
            return None

        scene_map = {"family": "family", "friends": "friends"}
        scene = scene_map.get(slots.scene, "generic")

        group_size = int(slots.group_size) if slots.group_size.isdigit() else (3 if scene == "family" else (4 if scene == "friends" else 2))
        duration_hours = int(slots.duration_hours) if slots.duration_hours.isdigit() else 5

        distance = slots.distance_preference if slots.distance_preference in ("近场", "可稍远") else "常规"
        travel = "walking" if slots.travel_mode == "walking" else "driving"

        preferences: list[str] = []
        dining_prefs: list[str] = []
        special_needs: list[str] = []

        if scene == "family":
            preferences.extend(["亲子友好", "照顾儿童节奏"])
            special_needs.append("适合儿童")
            if slots.child_age_hint:
                special_needs.append(f"儿童年龄约{slots.child_age_hint}")
        elif scene == "friends":
            preferences.extend(["社交氛围", "方便聊天互动"])
            special_needs.append("适合多人同行")

        if slots.dining_preference and slots.dining_preference != "需要餐饮安排":
            dining_prefs.append(slots.dining_preference)
        elif slots.dining_preference == "需要餐饮安排":
            preferences.append("需要餐饮安排")

        if slots.pace_preference == "轻松":
            preferences.append("少折腾")
        elif slots.pace_preference == "紧凑":
            preferences.append("内容更丰富")

        if slots.special_needs:
            # 直接把对话中捕获到的特殊需求落到结构化字段中，供 planner 与前端展示复用。
            special_needs.extend([item for item in slots.special_needs.split("、") if item])
        if slots.dining_preference in {"清淡减脂", "清淡"}:
            dining_prefs.append("清淡饮食")
            special_needs.append("清淡饮食")

        preferences = self._dedupe_list(preferences)
        dining_prefs = self._dedupe_list(dining_prefs)
        special_needs = self._dedupe_list(special_needs)

        constraints: list[dict[str, str]] = [
            {"key": "scene", "value": scene},
            {"key": "group_size", "value": str(group_size)},
            {"key": "duration_hours", "value": str(duration_hours)},
            {"key": "time_window", "value": slots.time_window or "下午"},
            {"key": "distance_preference", "value": distance},
            {"key": "pace_preference", "value": slots.pace_preference or "常规"},
            {"key": "travel_mode", "value": travel},
        ]
        if slots.city:
            constraints.append({"key": "city", "value": slots.city})
        if slots.child_age_hint:
            constraints.append({"key": "child_age_hint", "value": slots.child_age_hint})
        if dining_prefs:
            constraints.append({"key": "dining_preferences", "value": ",".join(dining_prefs)})
        if special_needs:
            constraints.append({"key": "special_needs", "value": "、".join(special_needs)})

        share_target = "家人" if scene == "family" else ("朋友" if scene == "friends" else "同行人")

        return {
            "raw_text": slots.goal or f"{slots.city or ''}{slots.time_window or '下午'}出行",
            "scene": scene,
            "group_size": group_size,
            "duration_hours": duration_hours,
            "time_window": slots.time_window or "下午",
            "distance_preference": distance,
            "city": slots.city,
            "origin_name": "",
            "origin_lat": None,
            "origin_lng": None,
            "travel_mode": travel,
            "child_age_hint": slots.child_age_hint,
            "share_target": share_target,
            "pace_preference": slots.pace_preference or "常规",
            "preferences": preferences,
            "dining_preferences": dining_prefs,
            "special_needs": special_needs,
            "constraints": constraints,
        }

    def _is_goal_ready(self, slots: ConversationSlots) -> bool:
        """只在核心规划字段完整时才允许生成 Goal。"""
        required = [
            slots.scene,
            slots.group_size,
            slots.time_window,
            slots.duration_hours,
            slots.distance_preference,
        ]
        if any(not item for item in required):
            return False
        if not slots.group_size.isdigit():
            return False
        if not slots.duration_hours.isdigit():
            return False
        return True

    def _dedupe_list(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

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
