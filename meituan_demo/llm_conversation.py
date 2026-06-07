from __future__ import annotations

import json
import logging
import os
import re as _re
from typing import Any

from openai import OpenAI

from .parser import GoalParser

logger = logging.getLogger("llm_conversation")

SYSTEM_PROMPT = """你是「美团本地活动规划助手」，通过自然对话收集用户需求。

## 对话策略

1. **正常收集**：用户说出需求后先理解认可，再自然追问 1 个缺失的关键信息。
2. **寒暄处理**：寒暄→友好回应引回正题；模糊/矛盾→温和指出。
3. **改口检测**：如果用户推翻了之前说过的话，要明确确认改口内容，然后继续追问。
4. **冲突提示**：如果新信息与已有约束产生矛盾，要温和指出并征求确认。
5. **主动复述**：当核心信息收集完毕时（scene, group_size, city, time_window, duration_hours 都有值），主动复述一遍完整需求让用户确认。
6. **距离理解**：**不要问"想去近一点还是远一点"**。distance_preference 默认"常规"，只有用户主动提到具体出发点时才设置。
7. **出发点收集**：不要主动追问出发点。如果用户主动说了具体位置（如"从公司附近"、"在西湖旁边"），记录即可。
8. **人数推断**：用户说"自己出去"、"一个人"、"自己逛逛"时，group_size 直接设为 1，不需要再问。
9. **信息充足即规划**：当 scene, group_size, city, time_window, duration_hours 都有值后，**立即**设置 ready_to_plan=true 并给出 goal 字段，不要再追问其他问题。

## ready_to_plan 条件
scene && group_size && city && time_window && duration_hours 都非空时**必须**设为 true。
一旦 ready_to_plan=true，你的 assistant_reply 应该是确认信息+告知用户正在规划，不要继续追问。"""

CONVERSATION_TOOL = {
    "type": "function",
    "function": {
        "name": "respond_as_activity_planner",
        "description": "回复用户并输出结构化需求字段",
        "parameters": {
            "type": "object",
            "properties": {
                "assistant_reply": {"type": "string"},
                "slots": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "scene": {"type": "string", "enum": ["family", "friends", "generic", ""]},
                        "group_size": {"type": "string"},
                        "city": {"type": "string"},
                        "time_window": {"type": "string", "enum": ["上午", "中午", "下午", "晚上", ""]},
                        "duration_hours": {"type": "string"},
                        "distance_preference": {"type": "string", "enum": ["近场", "可稍远", "常规", ""]},
                        "travel_mode": {"type": "string", "enum": ["driving", "walking", ""]},
                        "child_age_hint": {"type": "string"},
                        "dining_preference": {"type": "string"},
                        "pace_preference": {"type": "string", "enum": ["轻松", "紧凑", "常规", ""]},
                        "special_needs": {"type": "string"},
                    },
                    "required": ["goal", "scene", "group_size", "city", "time_window", "duration_hours", "travel_mode", "child_age_hint", "dining_preference", "pace_preference", "special_needs"],
                },
                "ready_to_plan": {"type": "boolean"},
                "suggested_replies": {"type": "array", "items": {"type": "string"}},
                "plan_text": {"type": "string"},
                "goal": {"type": "object", "description": "当 ready_to_plan 为 true 时必填的结构化 Goal"},

            },
            "required": ["assistant_reply", "slots", "ready_to_plan", "suggested_replies", "plan_text", "goal"],
        },
    },
}


class LLMConversationEngine:
    """LLM 驱动对话引擎。

    环境变量：
      OPENAI_API_KEY    — OpenAI 兼容 API 密钥
      DEEPSEEK_API_KEY  — 当 LLM_BASE_URL 含 deepseek 时自动选择
      LLM_MODEL         — 模型名（deepseek 场景默认 deepseek-chat）
      LLM_BASE_URL      — 自定义 API 端点（优先）
      OPENAI_BASE_URL   — 自定义 API 端点 fallback
    """

    def __init__(self, api_key=None, model=None, base_url=None):
        self._goal_parser = GoalParser()
        self._goal_required_fields = (
            "raw_text",
            "scene",
            "group_size",
            "city",
            "duration_hours",
            "time_window",
        )

        # ── 智能选择 Key ─────────────────────────────────
        user_key = api_key
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        env_model = os.environ.get("LLM_MODEL", "")
        env_base = os.environ.get("LLM_BASE_URL", "")

        if not user_key:
            user_model = model or env_model
            user_base = base_url or env_base
            is_deepseek = "deepseek" in (user_model + user_base).lower()
            if deepseek_key and not openai_key and not user_model and not user_base:
                # 只有 DeepSeek key 时，直接走 DeepSeek 默认配置，避免客户端初始化失败。
                is_deepseek = True
            user_key = deepseek_key if (is_deepseek and deepseek_key) else (openai_key or deepseek_key)

        using_deepseek = False
        if deepseek_key and user_key == deepseek_key:
            using_deepseek = True
        if "deepseek" in ((model or env_model) + (base_url or env_base)).lower():
            using_deepseek = True

        self._resolved_key = user_key
        self._model = model or env_model or ("deepseek-chat" if using_deepseek else "")
        self._client = None
        self._llm_disabled = False

        if not self._resolved_key:
            self._llm_disabled = True
            return

        # ── 确定 base_url ─────────────────────────────────
        resolved_base_url = (
            base_url
            or env_base
            or os.environ.get("OPENAI_BASE_URL", "")
        )

        if not resolved_base_url and using_deepseek:
            resolved_base_url = "https://api.deepseek.com/v1"

        if resolved_base_url:
            self._client = OpenAI(
                api_key=self._resolved_key, base_url=resolved_base_url,
                max_retries=0, timeout=5.0,
            )

    # ── 延迟初始化 ────────────────────────────────────────

    def _ensure_client(self):
        if self._llm_disabled:
            return None
        if self._client is not None:
            return self._client
        try:
            client = OpenAI(api_key=self._resolved_key, max_retries=0, timeout=3.0)
            client.chat.completions.create(model=self._model or "gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=1)
            self._client = client
            return client
        except Exception:
            self._llm_disabled = True
            return None

    def _service_error(self, detail: str) -> RuntimeError:
        return RuntimeError(f"对话服务暂时不可用，请检查服务器配置或网络连接。{detail}")

    # ── 规则降级 ─────────────────────────────────────────

    def _fallback_parse(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """LLM 不可用时，用 GoalParser 规则引擎兜底生成回复。"""
        user_texts = [
            str(item.get("content", "")).strip()
            for item in (messages or [])
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ]
        latest_user = user_texts[-1] if user_texts else ""

        # 用 GoalParser 解析用户最新输入
        context: dict[str, Any] = {}
        for item in reversed(messages or []):
            if item.get("role") == "user":
                content = str(item.get("content", "")).strip()
                if content:
                    break

        goal = self._goal_parser.parse(latest_user, context)

        # 从对话历史中补充缺失的槽位
        slots = {
            "goal": goal.raw_text,
            "scene": goal.scene or "",
            "group_size": str(goal.group_size) if goal.group_size else "",
            "city": goal.city or "",
            "time_window": goal.time_window or "",
            "duration_hours": str(goal.duration_hours) if goal.duration_hours else "",
            "distance_preference": goal.distance_preference or "",
            "travel_mode": goal.travel_mode or "",
            "child_age_hint": goal.child_age_hint or "",
            "dining_preference": ",".join(goal.dining_preferences) if goal.dining_preferences else "",
            "pace_preference": goal.pace_preference or "",
            "special_needs": ",".join(goal.special_needs) if goal.special_needs else "",
        }
        self._backfill_slots_from_history(slots, messages)

        has_enough = bool(slots.get("scene") and slots.get("group_size") and slots.get("city") and slots.get("time_window"))

        if has_enough:
            distance_text = f"，{slots.get('distance_preference', '常规')}距离" if slots.get("distance_preference", "常规") != "常规" else ""
            reply_text = (
                f"好的，我理解了你的需求：{slots['scene']}场景，{slots['group_size']}人，"
                f"{slots['time_window']}{slots.get('duration_hours', '4')}小时{distance_text}。"
                f"信息已经足够，我来帮你生成方案。"
            )
            goal_dict = {
                "raw_text": goal.raw_text or latest_user,
                "scene": slots["scene"],
                "group_size": int(slots["group_size"]),
                "duration_hours": int(slots.get("duration_hours") or "4"),
                "time_window": slots["time_window"],
                "distance_preference": slots.get("distance_preference", "常规"),
                "city": slots["city"],
                "origin_name": goal.origin_name,
                "origin_lat": goal.origin_lat,
                "origin_lng": goal.origin_lng,
                "travel_mode": slots.get("travel_mode", "driving"),
                "child_age_hint": slots.get("child_age_hint", ""),
                "share_target": goal.share_target,
                "pace_preference": slots.get("pace_preference", "常规"),
                "preferences": goal.preferences,
                "dining_preferences": slots.get("dining_preference", "").split(",") if slots.get("dining_preference") else [],
                "special_needs": slots.get("special_needs", "").split(",") if slots.get("special_needs") else [],
                "constraints": [{"key": c.key, "value": c.value} for c in goal.constraints],
            }
            # 直接使用 backfill 后的 slots，不再从 goal_dict 重建
            slots["goal"] = goal.raw_text or latest_user
            return {
                "assistant_reply": reply_text,
                "slots": slots,
                "ready_to_plan": True,
                "suggested_replies": ["开始规划", "再改一点"],
                "plan_text": goal.raw_text or latest_user,
                "goal": goal_dict,
            }

        # 信息不足时，生成追问
        missing = []
        if not slots.get("scene"):
            missing.append("是家庭出行还是朋友聚会")
        if not slots.get("group_size"):
            missing.append("大概几个人")
        if not slots.get("city"):
            missing.append("在哪个城市")
        if not slots.get("time_window"):
            missing.append("想上午、下午还是晚上出发")

        if missing:
            question = "我还想再确认几个信息：" + "、".join(missing) + "？"
        else:
            question = "能再跟我说说你更具体的偏好吗？比如想吃什么、想玩什么类型的活动？"

        return {
            "assistant_reply": question,
            "slots": slots,
            "ready_to_plan": False,
            "suggested_replies": self._generate_suggested_replies(slots),
            "plan_text": "",
            "goal": None,
        }

    # ── 公共接口 ─────────────────────────────────────────

    # ── 流式 JSON 解析 ────────────────────────────────────────

    def _stream_extract_text(self, json_str: str) -> str:
        """从流式累积的 function call JSON 中提取 assistant_reply 已出现部分。"""
        idx = json_str.find('"assistant_reply"')
        if idx < 0:
            return ""
        after_key = json_str[idx + len('"assistant_reply"'):]
        colon_match = _re.search(r'\s*:\s*"', after_key)
        if not colon_match:
            return ""
        start = idx + len('"assistant_reply"') + colon_match.end()
        result = []
        i = start
        while i < len(json_str):
            ch = json_str[i]
            if ch == '\\' and i + 1 < len(json_str):
                next_ch = json_str[i + 1]
                if next_ch == 'n':
                    result.append('\n')
                elif next_ch == 't':
                    result.append('\t')
                elif next_ch == 'r':
                    result.append('\r')
                elif next_ch == '\\':
                    result.append('\\')
                elif next_ch == '"':
                    result.append('"')
                elif next_ch == 'u' and i + 5 < len(json_str):
                    try:
                        result.append(chr(int(json_str[i + 2:i + 6], 16)))
                        i += 4
                    except (ValueError, IndexError):
                        result.append(ch)
                else:
                    result.append(next_ch)
                i += 2
                continue
            elif ch == '"':
                break
            result.append(ch)
            i += 1
        return ''.join(result)

    # ── 流式接口 ─────────────────────────────────────────

    def reply_stream(self, messages):
        """流式返回对话结果，逐 token 输出。

        产生事件字典：
          {"type": "token", "text": "..."}  — 文本 token
          {"type": "done", "slots": {...}, "ready_to_plan": bool,
           "suggested_replies": [...], "plan_text": "..."}
        """
        client = self._ensure_client()
        if client is None:
            logger.warning("LLM 客户端不可用，流式降级到规则引擎。")
            fallback = self._fallback_parse(messages)
            yield {"type": "token", "text": fallback["assistant_reply"]}
            yield {"type": "done",
                   "slots": fallback["slots"],
                   "ready_to_plan": fallback["ready_to_plan"],
                   "suggested_replies": fallback["suggested_replies"],
                   "plan_text": fallback["plan_text"],
                   "goal": fallback.get("goal")}
            return

        try:
            api_messages = self._build_msgs(messages)
            response = client.chat.completions.create(
                model=self._model,
                messages=api_messages,
                tools=[CONVERSATION_TOOL],
                tool_choice={"type": "function", "function": {"name": "respond_as_activity_planner"}},
                temperature=0.7,
                max_tokens=1024,
                stream=True,
                timeout=15.0,
            )

            accumulated_json = ""
            yielded_text_len = 0
            text_buffer = []
            tool_call_buffer = {"id": "", "type": "", "function": {"name": "", "arguments": ""}}
            collecting_tool = False

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 文本 token
                if delta.content:
                    text_buffer.append(delta.content)
                    yield {"type": "token", "text": delta.content}

                # 工具调用（function calling）—— 流式提取 assistant_reply 文本
                if delta.tool_calls:
                    collecting_tool = True
                    for tc in delta.tool_calls:
                        if tc.id:
                            tool_call_buffer["id"] = tc.id
                        if tc.function:
                            if tc.function.name and not tool_call_buffer["function"]["name"]:
                                tool_call_buffer["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_call_buffer["function"]["arguments"] += tc.function.arguments
                                accumulated_json += tc.function.arguments
                                current_text = self._stream_extract_text(accumulated_json)
                                if len(current_text) > yielded_text_len:
                                    new_text = current_text[yielded_text_len:]
                                    yielded_text_len = len(current_text)
                                    if new_text:
                                        yield {"type": "token", "text": new_text}

            if collecting_tool and tool_call_buffer["function"]["arguments"]:
                # 解析 function call 结果
                import json as _json
                parsed = _json.loads(tool_call_buffer["function"]["arguments"])
                normalized = self._normalize_parsed_response(parsed)
                normalized = self._finalize_confirmation_ready(messages, normalized)
                if normalized["ready_to_plan"] and normalized["goal"] is None:
                    raise self._service_error("模型返回的 Goal 结构不完整。")
                yield {"type": "done",
                       "slots": normalized["slots"],
                       "ready_to_plan": normalized["ready_to_plan"],
                       "suggested_replies": normalized["suggested_replies"],
                       "plan_text": normalized["plan_text"],
                       "goal": normalized.get("goal")}
            elif text_buffer:
                # LLM 返回了文本但没有 tool_calls —— 用 fallback 补充结构化数据
                logger.warning("LLM 返回了文本但无 tool_calls，使用 fallback 补充 slots。")
                fallback = self._fallback_parse(messages)
                yield {"type": "done",
                       "slots": fallback["slots"],
                       "ready_to_plan": fallback["ready_to_plan"],
                       "suggested_replies": fallback["suggested_replies"],
                       "plan_text": fallback["plan_text"],
                       "goal": fallback.get("goal")}
            else:
                raise self._service_error("模型未返回可解析的 tool_calls。")

        except Exception as exc:
            logger.warning("LLM 流式调用失败，降级到规则引擎: %s", exc)
            self._llm_disabled = True
            self._client = None
            fallback = self._fallback_parse(messages)
            yield {"type": "token", "text": fallback["assistant_reply"]}
            yield {"type": "done",
                   "slots": fallback["slots"],
                   "ready_to_plan": fallback["ready_to_plan"],
                   "suggested_replies": fallback["suggested_replies"],
                   "plan_text": fallback["plan_text"],
                   "goal": fallback.get("goal")}

    def _extract_slots(self, parsed):
        raw = parsed.get("slots", {}) or {}
        slots = {}
        for k in ["goal", "scene", "group_size", "city", "time_window",
                   "duration_hours", "distance_preference", "travel_mode",
                   "child_age_hint", "dining_preference", "pace_preference", "special_needs"]:
            v = raw.get(k, "")
            slots[k] = str(v) if v is not None else ""
        return slots

    def reply(self, messages):
        client = self._ensure_client()
        if client is None:
            logger.warning("LLM 客户端不可用，降级到规则引擎。")
            return self._fallback_parse(messages)
        try:
            return self._llm_reply(messages, client)
        except Exception as exc:
            logger.warning("LLM 调用失败，降级到规则引擎: %s", exc)
            self._llm_disabled = True
            self._client = None
            return self._fallback_parse(messages)

    # ── LLM 请求 ─────────────────────────────────────────

    def _llm_reply(self, messages, client):
        resp = client.chat.completions.create(
            model=self._model, messages=self._build_msgs(messages),
            tools=[CONVERSATION_TOOL],
            tool_choice={"type":"function","function":{"name":"respond_as_activity_planner"}},
            temperature=0.7, max_tokens=1024, timeout=10.0,
        )
        normalized = self._parse(resp)
        return self._finalize_confirmation_ready(messages, normalized)

    def _build_msgs(self, messages):
        return [{"role":"system","content":SYSTEM_PROMPT}] + (messages[-20:] if messages else [])

    def _parse(self, response):
        tc = response.choices[0].message.tool_calls
        if not tc:
            raise ValueError("no tool_calls")
        p = json.loads(tc[0].function.arguments)
        normalized = self._normalize_parsed_response(p)
        if normalized["ready_to_plan"] and normalized["goal"] is None:
            raise ValueError("goal missing when ready_to_plan")
        return normalized

    def _normalize_parsed_response(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """把 LLM 的 function call 结果收敛成稳定契约。"""
        slots = self._extract_slots(parsed)
        goal = self._normalize_goal(parsed.get("goal"))
        ready_to_plan = bool(parsed.get("ready_to_plan", False))

        if ready_to_plan and goal is None:
            ready_to_plan = False

        suggested = [str(r) for r in (parsed.get("suggested_replies") or []) if isinstance(r, str)][:3]

        result = {
            "assistant_reply": str(parsed.get("assistant_reply", "") or ""),
            "slots": slots,
            "ready_to_plan": ready_to_plan,
            "suggested_replies": suggested,
            "plan_text": str(parsed.get("plan_text", "") or ""),
            "goal": goal,
        }
        result = self._enforce_location_requirement(result)

        # 当未就绪时，始终用槽位状态生成追问选项（忽略 LLM 给的推荐内容）
        if not result.get("ready_to_plan"):
            result["suggested_replies"] = self._generate_suggested_replies(result.get("slots", {}))

        return result

    def _generate_suggested_replies(self, slots: dict[str, Any]) -> list[str]:
        """根据当前槽位状态自动生成追问快捷回复。"""
        if not slots.get("scene"):
            return ["家庭出行", "朋友聚会", "一个人逛逛"]
        if not slots.get("group_size"):
            return ["就我自己", "2-3个人", "4个人以上"]
        if not slots.get("city"):
            return ["我在福州", "杭州", "北京"]
        if not slots.get("time_window"):
            return ["上午", "下午", "晚上"]
        if not slots.get("duration_hours"):
            return ["1-2个小时", "半天", "一整天"]
        # 所有核心槽位都有了，提示确认
        return ["可以，就这样", "再改一点"]

    def _normalize_goal(self, goal_raw: Any) -> dict[str, Any] | None:
        """只接受字段完整的 Goal，避免把坏结构传给规划器。"""
        if not isinstance(goal_raw, dict) or not goal_raw:
            return None

        normalized = dict(goal_raw)
        for key in self._goal_required_fields:
            value = normalized.get(key)
            if value in (None, "", []):
                return None

        try:
            normalized["group_size"] = int(normalized["group_size"])
            duration_hours = self._coerce_duration_hours(normalized["duration_hours"])
            if duration_hours is None:
                return None
            normalized["duration_hours"] = duration_hours
        except (TypeError, ValueError):
            return None

        if not isinstance(normalized.get("constraints"), list):
            normalized["constraints"] = []
        if not isinstance(normalized.get("preferences"), list):
            normalized["preferences"] = []
        if not isinstance(normalized.get("dining_preferences"), list):
            normalized["dining_preferences"] = []
        if not isinstance(normalized.get("special_needs"), list):
            normalized["special_needs"] = []

        normalized.setdefault("city", "")
        normalized.setdefault("origin_name", "")
        normalized.setdefault("origin_lat", None)
        normalized.setdefault("origin_lng", None)
        normalized.setdefault("travel_mode", "driving")
        normalized.setdefault("child_age_hint", "")
        normalized.setdefault("share_target", "同行人")
        normalized.setdefault("pace_preference", "常规")
        return normalized

    def _finalize_confirmation_ready(self, messages, result: dict[str, Any]) -> dict[str, Any]:
        """用户明确确认时，为缺少少量默认字段的结果补齐可规划状态。"""
        if result.get("ready_to_plan") and result.get("goal") is not None:
            return result

        latest_user = ""
        for item in reversed(messages or []):
            if item.get("role") == "user":
                latest_user = str(item.get("content", "")).strip()
                break

        if not self._is_positive_confirmation(latest_user):
            return result

        slots = dict(result.get("slots") or {})

        # 从历史消息中补充缺失的槽位
        self._backfill_slots_from_history(slots, messages)

        # 确认语意味着用户接受当前理解，对缺失字段补默认值。
        slots.setdefault("goal", latest_user)
        if not slots.get("goal"):
            slots["goal"] = latest_user
        if not slots.get("scene"):
            slots["scene"] = "generic"
        if not slots.get("group_size"):
            # 从历史消息推断人数
            all_text = " ".join(str(m.get("content", "")) for m in (messages or []) if m.get("role") == "user")
            if any(w in all_text for w in ["自己", "一个人", "自己逛"]):
                slots["group_size"] = "1"
            else:
                slots["group_size"] = "2"
        if not slots.get("city"):
            # 没有城市信息，不能进入规划
            return result
        if not slots.get("time_window"):
            slots["time_window"] = "下午"
        if not slots.get("duration_hours"):
            slots["duration_hours"] = "4"
        else:
            normalized_duration = self._coerce_duration_hours(slots.get("duration_hours"))
            if normalized_duration is not None:
                slots["duration_hours"] = str(normalized_duration)
        if not slots.get("distance_preference"):
            slots["distance_preference"] = "常规"
        if not slots.get("travel_mode"):
            slots["travel_mode"] = "driving"
        if not slots.get("pace_preference"):
            slots["pace_preference"] = "常规"

        goal = self._build_goal_from_slots(slots, messages)
        if goal is None:
            return result

        result["slots"] = slots
        result["goal"] = goal
        result["ready_to_plan"] = True
        result["assistant_reply"] = "好，那我就按这版先帮你出方案。"
        result["plan_text"] = goal["raw_text"]
        if not result.get("suggested_replies"):
            result["suggested_replies"] = ["开始规划", "再改一点"]
        return self._enforce_location_requirement(result)

    def _backfill_slots_from_history(self, slots: dict[str, Any], messages: list[dict[str, Any]] | None) -> None:
        """从对话历史中提取并补充缺失的槽位值。"""
        all_user_text = " ".join(
            str(m.get("content", "")).strip()
            for m in (messages or [])
            if m.get("role") == "user"
        )

        if not slots.get("scene"):
            if any(w in all_user_text for w in ["老婆", "老公", "孩子", "宝宝", "带娃", "亲子", "家庭", "家人"]):
                slots["scene"] = "family"
            elif any(w in all_user_text for w in ["朋友", "同学", "同事", "闺蜜", "兄弟", "聚会"]):
                slots["scene"] = "friends"
            elif any(w in all_user_text for w in ["自己", "一个人", "自己逛"]):
                slots["scene"] = "generic"

        # 人数检测：明确表达（"自己"/"一个人"）优先级高于默认值
        if any(w in all_user_text for w in ["自己", "一个人", "自己逛", "独自"]):
            slots["group_size"] = "1"
        elif "两大一小" in all_user_text:
            slots["group_size"] = "3"
        elif not slots.get("group_size"):
            import re
            m = re.search(r"([0-9一二两三四五六七八九十]+)\s*个?人", all_user_text)
            if m:
                mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5}
                token = m.group(1)
                slots["group_size"] = str(int(token) if token.isdigit() else mapping.get(token, 2))

        if not slots.get("city"):
            for m in (messages or []):
                if m.get("role") == "user":
                    content = str(m.get("content", ""))
                    # 匹配"在XX"或纯城市名
                    import re
                    city_match = re.search(r"在([一-龥]{2,4})", content)
                    if city_match:
                        candidate = city_match.group(1)
                        if candidate not in ("福州大学", "附近", "这边", "公司"):
                            slots["city"] = candidate
                            break

        if not slots.get("time_window"):
            if "上午" in all_user_text or "早上" in all_user_text:
                slots["time_window"] = "上午"
            elif "中午" in all_user_text:
                slots["time_window"] = "中午"
            elif "晚上" in all_user_text:
                slots["time_window"] = "晚上"
            else:
                slots["time_window"] = "下午"

        if not slots.get("duration_hours"):
            duration_hours = self._coerce_duration_hours(all_user_text)
            if duration_hours is not None:
                slots["duration_hours"] = str(duration_hours)
            elif "半天" in all_user_text:
                slots["duration_hours"] = "4"

    def _is_positive_confirmation(self, text: str) -> bool:
        compact = _re.sub(r"\s+", "", str(text or "")).lower()
        if not compact:
            return False
        patterns = [
            r"(就按这个来|按这个来|就这么定|就这样吧|开始吧|可以开始了|没问题就这样|确认|通过)",
            r"(很满意|满意|挺好|很好|可以|行|好的|ok|okay|yes)",
            r"(推荐.*方案|开始规划|出方案|帮我规划|帮我安排|生成方案|看看方案|给我看看)",
        ]
        return any(_re.search(pattern, compact) for pattern in patterns)

    def _has_confirmation_ready_slots(self, slots: dict[str, Any]) -> bool:
        return bool(
            slots.get("goal")
            and slots.get("scene")
            and slots.get("group_size")
            and slots.get("city")
            and slots.get("time_window")
        )

    def _enforce_location_requirement(self, result: dict[str, Any]) -> dict[str, Any]:
        """地点是进入规划前的必问项，缺失时强制回到追问地点。"""
        slots = dict(result.get("slots") or {})
        if slots.get("city"):
            return result

        # 只有在其他核心信息已经差不多时，才明确把追问收敛到地点。
        has_enough_context = bool(
            slots.get("scene")
            and slots.get("group_size")
            and slots.get("time_window")
            and slots.get("duration_hours")
        )
        if not has_enough_context:
            return result

        result["ready_to_plan"] = False
        result["goal"] = None
        result["assistant_reply"] = '还差一个位置信息：你们现在在哪个城市？比如"我在福州"或"从杭州西湖附近出发"都行。'
        result["suggested_replies"] = ["我在福州", "杭州", "北京"]
        result["plan_text"] = ""
        return result

    def _build_goal_from_slots(self, slots: dict[str, Any], messages) -> dict[str, Any] | None:
        try:
            group_size = int(slots.get("group_size", ""))
        except (TypeError, ValueError):
            return None

        duration_hours = self._coerce_duration_hours(slots.get("duration_hours", ""))
        if duration_hours is None:
            return None

        raw_text = self._build_raw_text_from_slots(slots, messages)
        if not raw_text:
            return None

        dining_preferences = [slots["dining_preference"]] if slots.get("dining_preference") else []
        special_needs = [slots["special_needs"]] if slots.get("special_needs") else []
        preferences: list[str] = []
        if slots.get("pace_preference") == "轻松":
            preferences.append("轻松安排")
        elif slots.get("pace_preference") == "紧凑":
            preferences.append("内容丰富")

        constraints = []
        for key in [
            "scene",
            "group_size",
            "duration_hours",
            "time_window",
            "distance_preference",
            "travel_mode",
            "city",
            "child_age_hint",
            "dining_preference",
            "pace_preference",
        ]:
            value = slots.get(key, "")
            if value:
                constraints.append({"key": key, "value": str(value)})

        return self._normalize_goal(
            {
                "raw_text": raw_text,
                "scene": slots.get("scene", "generic"),
                "group_size": group_size,
                "duration_hours": duration_hours,
                "time_window": slots.get("time_window", ""),
                "distance_preference": slots.get("distance_preference", "常规"),
                "city": slots.get("city", ""),
                "origin_name": "",
                "origin_lat": None,
                "origin_lng": None,
                "travel_mode": slots.get("travel_mode", "driving"),
                "child_age_hint": slots.get("child_age_hint", ""),
                "share_target": "同行人",
                "pace_preference": slots.get("pace_preference", "常规"),
                "preferences": preferences,
                "dining_preferences": dining_preferences,
                "special_needs": special_needs,
                "constraints": constraints,
            }
        )

    def _coerce_duration_hours(self, value: Any) -> int | None:
        """把“1-2个小时”“2~3小时”“半天”这类时长表达收敛成规划器可用的整数小时。"""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return min(max(int(value), 1), 12)

        text = str(value).strip()
        if not text:
            return None

        compact = _re.sub(r"\s+", "", text)
        if compact in {"半天"}:
            return 4
        if compact in {"一整天", "全天"}:
            return 8
        if compact.isdigit():
            return min(max(int(compact), 1), 12)

        range_match = _re.search(r"(\d+)\s*[-~到至]\s*(\d+)", compact)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            return min(max(max(start, end), 1), 12)

        hour_match = _re.search(r"(\d+)\s*个?小时", compact)
        if hour_match:
            return min(max(int(hour_match.group(1)), 1), 12)

        return None

    def _build_raw_text_from_slots(self, slots: dict[str, Any], messages) -> str:
        if slots.get("goal"):
            pieces = []
            if slots.get("city"):
                pieces.append(f"在{slots['city']}")
            if slots.get("time_window"):
                pieces.append(slots["time_window"])
            if slots.get("scene") == "family":
                pieces.append(f"{slots.get('group_size', '')}人家庭出行")
            elif slots.get("scene") == "friends":
                pieces.append(f"{slots.get('group_size', '')}人朋友聚会")
            elif slots.get("group_size"):
                pieces.append(f"{slots['group_size']}人出行")
            pieces.append(slots["goal"])
            if slots.get("duration_hours"):
                pieces.append(f"{slots['duration_hours']}小时左右")
            if slots.get("distance_preference"):
                pieces.append(slots["distance_preference"])
            return "，".join([item for item in pieces if item])

        user_texts = [
            str(item.get("content", "")).strip()
            for item in (messages or [])
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ]
        if len(user_texts) >= 2:
            return user_texts[-2]
        return user_texts[-1] if user_texts else ""
