from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SceneType = Literal["family", "friends", "generic"]
CandidateType = Literal["activity", "restaurant", "addon"]
ActionType = Literal["reserve", "queue", "order", "delivery", "share"]
ActionStatus = Literal["success", "failed", "skipped"]
TravelMode = Literal["walking", "driving"]


@dataclass(slots=True)
class Constraint:
    key: str
    value: str


@dataclass(slots=True)
class Goal:
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
    share_target: str = "同行人"
    pace_preference: str = "常规"
    _weather_is_bad: bool = field(default=False, init=False, repr=False)
    preferences: list[str] = field(default_factory=list)
    dining_preferences: list[str] = field(default_factory=list)
    special_needs: list[str] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)


@dataclass(slots=True)
class Candidate:
    name: str
    category: CandidateType
    tags: list[str]
    duration_minutes: int
    area: str
    price_level: str
    family_friendly: bool
    availability: str
    address: str = ""
    business_area: str = ""
    source: str = "mock"
    poi_id: str = ""
    lat: float | None = None
    lng: float | None = None
    distance_meters: int = 0
    travel_minutes: int = 0
    score: float = 0.0
    reason: str = ""


@dataclass(slots=True)
class ItineraryStop:
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


@dataclass(slots=True)
class ScoreBreakdownItem:
    label: str
    score: float
    detail: str


@dataclass(slots=True)
class Itinerary:
    title: str
    total_minutes: int
    stops: list[ItineraryStop]
    rationale: list[str]
    score: float = 0.0
    total_travel_minutes: int = 0
    route_summary: list[str] = field(default_factory=list)
    map_center_lat: float | None = None
    map_center_lng: float | None = None
    alerts: list[str] = field(default_factory=list)
    fallback_options: list[str] = field(default_factory=list)
    score_breakdown: list[ScoreBreakdownItem] = field(default_factory=list)
    recommendation_reason: str = ""
    planning_basis: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionAction:
    action_type: ActionType
    target: str
    payload: dict[str, str]


@dataclass(slots=True)
class ExecutionResult:
    action_type: ActionType
    target: str
    status: ActionStatus
    message: str
    reference_id: str = ""
    recovery_hint: str = ""
    details: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PlanningOutput:
    goal: Goal
    itinerary: Itinerary
    actions: list[ExecutionAction]
    data_mode: str = "mock"
    alternatives: list[Itinerary] = field(default_factory=list)
    recommendation_reason: str = ""


@dataclass(slots=True)
class AgentOutput:
    planning: PlanningOutput
    execution_results: list[ExecutionResult]
    share_text: str
    summary: list[str] = field(default_factory=list)
