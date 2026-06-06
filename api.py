from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from dataclasses import asdict
from typing import Any
import os

from meituan_demo.agent import LocalActivityAgent
from meituan_demo.llm_conversation import LLMConversationEngine
from meituan_demo.models import (
    ActionType,
    CandidateType,
    Constraint,
    Goal,
    Itinerary,
    ItineraryStop,
    PlanningOutput,
    SceneType,
    TravelMode,
    ExecutionAction,
    AgentOutput,
    ScoreBreakdownItem,
)

app = FastAPI(title="Meituan Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 规划与对话分开编排，便于前端先澄清需求，再进入正式规划。
agent = LocalActivityAgent()
conversation = LLMConversationEngine()


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    assistant_reply: str
    slots: dict[str, str] = Field(default_factory=dict)
    ready_to_plan: bool = False
    suggested_replies: list[str] = Field(default_factory=list)
    plan_text: str = ""


class PlanRequest(BaseModel):
    user_text: str
    city: str = ""
    origin_name: str = ""
    origin_lat: float | None = None
    origin_lng: float | None = None
    travel_mode: TravelMode = "driving"


class ConstraintIn(BaseModel):
    key: str
    value: str


class GoalIn(BaseModel):
    raw_text: str
    scene: SceneType
    group_size: int
    duration_hours: int
    time_window: str
    distance_preference: str
    city: str = ""
    origin_name: str = ""
    origin_lat: float | None = None
    origin_lng: float | None = None
    travel_mode: TravelMode = "driving"
    child_age_hint: str = ""
    pace_preference: str = "常规"
    preferences: list[str] = Field(default_factory=list)
    dining_preferences: list[str] = Field(default_factory=list)
    special_needs: list[str] = Field(default_factory=list)
    constraints: list[ConstraintIn] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ItineraryStopIn(BaseModel):
    start_time: str
    duration_minutes: int
    title: str
    category: CandidateType
    location: str
    note: str
    address: str = ""
    business_area: str = ""
    source: str = "mock"
    lat: float | None = None
    lng: float | None = None
    distance_from_prev_meters: int = 0
    travel_minutes_from_prev: int = 0

    model_config = ConfigDict(extra="ignore")


class ItineraryIn(BaseModel):
    title: str
    total_minutes: int
    stops: list[ItineraryStopIn]
    rationale: list[str] = Field(default_factory=list)
    score: float = 0.0
    total_travel_minutes: int = 0
    route_summary: list[str] = Field(default_factory=list)
    map_center_lat: float | None = None
    map_center_lng: float | None = None
    alerts: list[str] = Field(default_factory=list)
    fallback_options: list[str] = Field(default_factory=list)
    score_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    recommendation_reason: str = ""
    planning_basis: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ExecutionActionIn(BaseModel):
    action_type: ActionType
    target: str
    payload: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PlanningOutputIn(BaseModel):
    goal: GoalIn
    itinerary: ItineraryIn
    actions: list[ExecutionActionIn] = Field(default_factory=list)
    data_mode: str = "mock"
    alternatives: list[ItineraryIn] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ExecutionResultOut(BaseModel):
    action_type: ActionType
    target: str
    status: str
    message: str
    reference_id: str = ""
    recovery_hint: str = ""
    details: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PlanningOutputOut(BaseModel):
    goal: GoalIn
    itinerary: ItineraryIn
    actions: list[ExecutionActionIn] = Field(default_factory=list)
    data_mode: str = "mock"
    alternatives: list[ItineraryIn] = Field(default_factory=list)
    recommendation_reason: str = ""

    model_config = ConfigDict(extra="ignore")


class AgentOutputOut(BaseModel):
    planning: PlanningOutputOut
    execution_results: list[ExecutionResultOut] = Field(default_factory=list)
    share_text: str
    summary: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


@app.post("/chat", response_model=ChatResponse)
def chat_activity(req: ChatRequest):
    # /chat 只负责多轮澄清与槽位整理，不直接执行正式规划。
    try:
        return conversation.reply([item.model_dump() for item in req.messages])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat endpoint."""
    import json as _json
    def gen():
        try:
            for ev in conversation.reply_stream([item.model_dump() for item in req.messages]):
                yield "data: " + _json.dumps(ev, ensure_ascii=False) + chr(10) + chr(10)
        except Exception:
            yield "data: " + _json.dumps({"type": "error", "text": "chat error"}, ensure_ascii=False) + chr(10) + chr(10)
        yield "data: [DONE]" + chr(10) + chr(10)
    return StreamingResponse(gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
@app.post("/plan", response_model=PlanningOutputOut)
def plan_activity(req: PlanRequest):
    # 当前端确认信息足够后，再把整理后的自然语言交给规划器生成方案。
    try:
        planning = agent.plan(
            req.user_text,
            {
                "city": req.city,
                "origin_name": req.origin_name,
                "origin_lat": req.origin_lat,
                "origin_lng": req.origin_lng,
                "travel_mode": req.travel_mode,
            },
        )
        return _serialize_planning(planning)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute", response_model=AgentOutputOut)
def execute_activity(planning_data: PlanningOutputIn):
    # 执行接口接收前端确认过的方案，并转换回内部 dataclass 结构。
    try:
        goal_data = planning_data.goal.model_dump()
        goal_data["constraints"] = [
            Constraint(**c.model_dump()) for c in planning_data.goal.constraints
        ]
        goal = Goal(**goal_data)

        itinerary_data = planning_data.itinerary.model_dump()
        itinerary_data["score_breakdown"] = [
            ScoreBreakdownItem(**item) for item in itinerary_data.get("score_breakdown", [])
        ]
        itinerary_data["stops"] = [
            ItineraryStop(**s.model_dump()) for s in planning_data.itinerary.stops
        ]
        itinerary = Itinerary(**itinerary_data)

        actions = [
            ExecutionAction(**a.model_dump()) for a in planning_data.actions
        ]

        alternatives = []
        for alt in planning_data.alternatives:
            alt_data = alt.model_dump()
            alt_data["score_breakdown"] = [
                ScoreBreakdownItem(**item) for item in alt_data.get("score_breakdown", [])
            ]
            alt_data["stops"] = [ItineraryStop(**s.model_dump()) for s in alt.stops]
            alternatives.append(Itinerary(**alt_data))

        planning_output = PlanningOutput(
            goal=goal,
            itinerary=itinerary,
            actions=actions,
            alternatives=alternatives
        )

        output = agent.execute(planning_output)
        return _serialize_execution(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_planning(planning: PlanningOutput) -> dict[str, Any]:
    # 统一把内部 dataclass 输出成前端可直接消费的 JSON 结构。
    return {
        "goal": asdict(planning.goal),
        "itinerary": _serialize_itinerary(planning.itinerary),
        "actions": [asdict(action) for action in planning.actions],
        "alternatives": [_serialize_itinerary(item) for item in planning.alternatives],
        "data_mode": planning.data_mode,
        "recommendation_reason": planning.recommendation_reason,
    }


def _serialize_itinerary(itinerary: Itinerary) -> dict[str, Any]:
    return {
        "title": itinerary.title,
        "total_minutes": itinerary.total_minutes,
        "stops": [asdict(stop) for stop in itinerary.stops],
        "rationale": itinerary.rationale,
        "score": itinerary.score,
        "total_travel_minutes": itinerary.total_travel_minutes,
        "route_summary": itinerary.route_summary,
        "map_center_lat": itinerary.map_center_lat,
        "map_center_lng": itinerary.map_center_lng,
        "alerts": itinerary.alerts,
        "fallback_options": itinerary.fallback_options,
        "score_breakdown": [asdict(item) for item in itinerary.score_breakdown],
        "recommendation_reason": itinerary.recommendation_reason,
        "planning_basis": itinerary.planning_basis,
    }


def _serialize_execution(output: AgentOutput) -> dict[str, Any]:
    return {
        "planning": _serialize_planning(output.planning),
        "execution_results": [asdict(result) for result in output.execution_results],
        "share_text": output.share_text,
        "summary": output.summary,
    }


# Frontend SPA serving
from fastapi.staticfiles import StaticFiles
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dir, "assets")), name="frontend_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        from fastapi.responses import FileResponse
        if full_path in ("favicon.svg",):
            return FileResponse(os.path.join(_frontend_dir, full_path))
        return FileResponse(os.path.join(_frontend_dir, "index.html"))
