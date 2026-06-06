from __future__ import annotations

import json
import logging
import os
import re as _re
from typing import Any

from openai import OpenAI

from .conversation import ConversationOrchestrator

logger = logging.getLogger("llm_conversation")

SYSTEM_PROMPT = """你是「美团本地活动规划助手」，通过自然对话收集用户需求。

对话策略：
- 用户说出需求后先理解认可，再自然追问 1 个缺失的关键信息
- 寒暄→友好回应引回正题；模糊/矛盾→温和指出
- 用户没提的字段保持已有值不变

ready_to_plan = true 条件：scene && group_size && time_window && duration_hours && distance_preference 都非空"""

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
                        "pace_preference": {"type": "string", "enum": ["轻松", "紧湊", "常规", ""]},
                        "special_needs": {"type": "string"},
                    },
                    "required": ["goal", "scene", "group_size", "city", "time_window", "duration_hours", "distance_preference", "travel_mode", "child_age_hint", "dining_preference", "pace_preference", "special_needs"],
                },
                "ready_to_plan": {"type": "boolean"},
                "suggested_replies": {"type": "array", "items": {"type": "string"}},
                "plan_text": {"type": "string"},
            },
            "required": ["assistant_reply", "slots", "ready_to_plan", "suggested_replies", "plan_text"],
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
        self._fallback = ConversationOrchestrator()

        # ── 智能选择 Key ─────────────────────────────────
        user_key = api_key
        if not user_key:
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
            user_model = model or os.environ.get("LLM_MODEL", "")
            user_base = base_url or os.environ.get("LLM_BASE_URL", "")
            is_deepseek = "deepseek" in (user_model + user_base).lower()
            user_key = deepseek_key if (is_deepseek and deepseek_key) else (openai_key or deepseek_key)

        self._resolved_key = user_key
        self._model = model or os.environ.get("LLM_MODEL", "deepseek-chat" if "deepseek" in (os.environ.get("LLM_BASE_URL", "") or "").lower() else "")
        self._client = None
        self._llm_disabled = False

        if not self._resolved_key:
            self._llm_disabled = True
            return

        # ── 确定 base_url ─────────────────────────────────
        resolved_base_url = (
            base_url
            or os.environ.get("LLM_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL", "")
        )

        if not resolved_base_url and self._model in ("deepseek-chat", "deepseek-reasoner"):
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
            # 规则引擎降级：一次返回全部文本
            result = self._fallback.reply(messages)
            yield {"type": "token", "text": result["assistant_reply"]}
            yield {"type": "done",
                   "slots": result["slots"],
                   "ready_to_plan": result["ready_to_plan"],
                   "suggested_replies": result["suggested_replies"],
                   "plan_text": result["plan_text"]}
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
                slots = self._extract_slots(parsed)
                yield {"type": "done",
                       "slots": slots,
                       "ready_to_plan": bool(parsed.get("ready_to_plan", False)),
                       "suggested_replies": [str(r) for r in (parsed.get("suggested_replies") or []) if isinstance(r, str)][:3],
                       "plan_text": str(parsed.get("plan_text", "") or "")}
            else:
                # 没有 tool_calls，把已积累的文本作为一次回复
                full_text = "".join(text_buffer)
                result = self._fallback.reply(messages)
                yield {"type": "token", "text": full_text or result["assistant_reply"]}
                yield {"type": "done",
                       "slots": result["slots"],
                       "ready_to_plan": result["ready_to_plan"],
                       "suggested_replies": result["suggested_replies"],
                       "plan_text": result["plan_text"]}

        except Exception:
            self._llm_disabled = True
            self._client = None
            result = self._fallback.reply(messages)
            yield {"type": "token", "text": result["assistant_reply"]}
            yield {"type": "done",
                   "slots": result["slots"],
                   "ready_to_plan": result["ready_to_plan"],
                   "suggested_replies": result["suggested_replies"],
                   "plan_text": result["plan_text"]}

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
            return self._fallback.reply(messages)
        try:
            return self._llm_reply(messages, client)
        except Exception:
            self._llm_disabled = True; self._client = None
            return self._fallback.reply(messages)

    # ── LLM 请求 ─────────────────────────────────────────

    def _llm_reply(self, messages, client):
        resp = client.chat.completions.create(
            model=self._model, messages=self._build_msgs(messages),
            tools=[CONVERSATION_TOOL],
            tool_choice={"type":"function","function":{"name":"respond_as_activity_planner"}},
            temperature=0.7, max_tokens=1024, timeout=10.0,
        )
        return self._parse(resp)

    def _build_msgs(self, messages):
        return [{"role":"system","content":SYSTEM_PROMPT}] + (messages[-20:] if messages else [])

    def _parse(self, response):
        tc = response.choices[0].message.tool_calls
        if not tc:
            raise ValueError("no tool_calls")
        p = json.loads(tc[0].function.arguments)
        raw = p.get("slots", {}) or {}
        slots = {k: str(raw.get(k,"") or "") for k in [
            "goal","scene","group_size","city","time_window",
            "duration_hours","distance_preference","travel_mode",
            "child_age_hint","dining_preference","pace_preference","special_needs",
        ]}
        return {
            "assistant_reply": str(p.get("assistant_reply","")),
            "slots": slots,
            "ready_to_plan": bool(p.get("ready_to_plan",False)),
            "suggested_replies": [str(r) for r in (p.get("suggested_replies") or []) if isinstance(r,str)][:3],
            "plan_text": str(p.get("plan_text","") or ""),
        }
