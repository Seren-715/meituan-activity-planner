from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from .models import Candidate, ExecutionAction, ExecutionResult, Goal


class MockToolbox:
    """比赛版数据层：优先使用真实高德能力，失败时回退到本地 Mock。"""

    def __init__(self) -> None:
        self.scenario = os.environ.get("MEITUAN_DEMO_SCENARIO", "normal").strip().lower() or "normal"
        self.amap_service_key = os.environ.get("AMAP_WEB_SERVICE_KEY", "").strip()
        self.last_data_mode = "mock"
        self._route_cache: dict[tuple[str, str, str], tuple[int, int]] = {}

    def search_activities(self, goal: Goal) -> list[Candidate]:
        real_candidates = self._search_real_candidates(goal, category="activity")
        if real_candidates:
            self.last_data_mode = "real"
            return self._apply_scenario(real_candidates)
        items = [
            Candidate(
                name="室内亲子乐园",
                category="activity",
                tags=["亲子", "室内", "低折腾"],
                duration_minutes=120,
                area="社区商圈",
                price_level="medium",
                family_friendly=True,
                availability="available",
                address="社区商圈 1 号",
                business_area="社区商圈",
                score=8.9,
                reason="适合亲子场景，路程短，天气影响小。",
            ),
            Candidate(
                name="社区手作体验馆",
                category="activity",
                tags=["亲子", "手作", "雨天可行"],
                duration_minutes=100,
                area="社区商圈",
                price_level="low",
                family_friendly=True,
                availability="available",
                address="社区商圈 18 号",
                business_area="社区商圈",
                score=8.1,
                reason="适合带孩子动手参与，节奏更平缓。",
            ),
            Candidate(
                name="沉浸式剧本体验馆",
                category="activity",
                tags=["社交", "互动", "朋友局"],
                duration_minutes=150,
                area="核心商圈",
                price_level="medium",
                family_friendly=False,
                availability="available",
                address="核心商圈 88 号",
                business_area="核心商圈",
                score=8.5,
                reason="适合朋友聚会，互动感强。",
            ),
            Candidate(
                name="保龄球社交馆",
                category="activity",
                tags=["社交", "轻竞技", "朋友局"],
                duration_minutes=110,
                area="次核心商圈",
                price_level="medium",
                family_friendly=False,
                availability="available",
                address="次核心商圈 33 号",
                business_area="次核心商圈",
                score=8.3,
                reason="上手门槛低，适合多人轻社交。",
            ),
            Candidate(
                name="城市公园轻徒步",
                category="activity",
                tags=["户外", "轻松", "低成本"],
                duration_minutes=90,
                area="近场公园",
                price_level="low",
                family_friendly=True,
                availability="available",
                address="近场公园东门",
                business_area="近场公园",
                score=8.2,
                reason="距离近，节奏舒缓，适合短时放松。",
            ),
        ]
        self.last_data_mode = "mock"
        return self._apply_scenario(items)

    def search_restaurants(self, goal: Goal) -> list[Candidate]:
        real_candidates = self._search_real_candidates(goal, category="restaurant")
        if real_candidates:
            self.last_data_mode = "real"
            return self._apply_scenario(real_candidates)
        items = [
            Candidate(
                name="家常菜亲子餐厅",
                category="restaurant",
                tags=["亲子座椅", "家常菜", "清淡可选"],
                duration_minutes=90,
                area="社区商圈",
                price_level="medium",
                family_friendly=True,
                availability="queue_15m",
                address="社区商圈 5 号",
                business_area="社区商圈",
                score=8.8,
                reason="适合家庭聚餐，排队时间可接受。",
            ),
            Candidate(
                name="热闹烤肉店",
                category="restaurant",
                tags=["朋友聚餐", "气氛好"],
                duration_minutes=100,
                area="核心商圈",
                price_level="medium",
                family_friendly=False,
                availability="available",
                address="核心商圈 29 号",
                business_area="核心商圈",
                score=8.7,
                reason="适合多人朋友场景，执行成功率高。",
            ),
            Candidate(
                name="轻食简餐吧",
                category="restaurant",
                tags=["轻食", "快捷", "少负担"],
                duration_minutes=70,
                area="近场公园",
                price_level="low",
                family_friendly=True,
                availability="available",
                address="近场公园南侧",
                business_area="近场公园",
                score=8.0,
                reason="适合清淡偏好，衔接顺畅。",
            ),
            Candidate(
                name="港式茶餐厅",
                category="restaurant",
                tags=["出餐稳定", "朋友聚餐", "儿童友好"],
                duration_minutes=80,
                area="社区商圈",
                price_level="medium",
                family_friendly=True,
                availability="available",
                address="社区商圈 12 号",
                business_area="社区商圈",
                score=8.4,
                reason="上菜稳定、口味覆盖广，适合作为稳妥餐饮备选。",
            ),
            Candidate(
                name="川味小馆",
                category="restaurant",
                tags=["重口味", "朋友聚餐", "下饭"],
                duration_minutes=85,
                area="次核心商圈",
                price_level="low",
                family_friendly=False,
                availability="available",
                address="次核心商圈 16 号",
                business_area="次核心商圈",
                score=7.9,
                reason="适合偏重口味的朋友聚餐，但不适合清淡需求。",
            ),
        ]
        self.last_data_mode = "mock"
        return self._apply_scenario(items)

    def search_addons(self, goal: Goal) -> list[Candidate]:
        real_candidates = self._search_real_candidates(goal, category="addon")
        if real_candidates:
            self.last_data_mode = "real"
            return self._apply_scenario(real_candidates)
        items = [
            Candidate(
                name="甜品补给站",
                category="addon",
                tags=["收尾", "轻社交"],
                duration_minutes=45,
                area="同商圈",
                price_level="low",
                family_friendly=True,
                availability="available",
                address="同商圈 A1",
                business_area="同商圈",
                score=7.8,
                reason="作为收尾补充，保持 4-6 小时完整闭环。",
            ),
            Candidate(
                name="河边散步收尾",
                category="addon",
                tags=["轻松", "散步", "低成本"],
                duration_minutes=40,
                area="近场公园",
                price_level="low",
                family_friendly=True,
                availability="available",
                address="近场公园沿河步道",
                business_area="近场公园",
                score=7.7,
                reason="餐后轻松散步，适合少折腾场景。",
            ),
            Candidate(
                name="桌游放松局",
                category="addon",
                tags=["社交", "聊天", "雨天可行"],
                duration_minutes=60,
                area="核心商圈",
                price_level="medium",
                family_friendly=False,
                availability="available",
                address="核心商圈 61 号",
                business_area="核心商圈",
                score=7.9,
                reason="适合朋友场景的低门槛续摊。",
            ),
        ]
        self.last_data_mode = "mock"
        return self._apply_scenario(items)

    def search_candidates(self, goal: Goal) -> dict[str, list[Candidate]]:
        return {
            "activities": self.search_activities(goal),
            "restaurants": self.search_restaurants(goal),
            "addons": self.search_addons(goal),
        }

    def check_availability(self, candidate: Candidate) -> tuple[bool, str]:
        if self.scenario == "availability_timeout" and candidate.category == "restaurant":
            return False, "可用性查询超时"
        if candidate.availability == "available":
            return True, "资源可用"
        if candidate.availability.startswith("queue_"):
            wait_time = candidate.availability.split("_", maxsplit=1)[1]
            return True, f"需要等待 {wait_time}"
        return False, "资源不可用"

    def estimate_transition(self, goal: Goal, source: Candidate | None, target: Candidate) -> tuple[int, int]:
        if source is None:
            if goal.origin_lat is not None and goal.origin_lng is not None and target.lat is not None and target.lng is not None:
                duration, distance = self._fetch_route_minutes(
                    goal.origin_lng,
                    goal.origin_lat,
                    target.lng,
                    target.lat,
                    goal.travel_mode,
                )
                if duration > 0:
                    return duration, distance
        elif source.lat is not None and source.lng is not None and target.lat is not None and target.lng is not None:
            duration, distance = self._fetch_route_minutes(source.lng, source.lat, target.lng, target.lat, goal.travel_mode)
            if duration > 0:
                return duration, distance

        distance = self._fallback_distance(source, target)
        base_speed = 80 if goal.travel_mode == "walking" else 400  # 米/分钟
        duration = max(5, math.ceil(distance / base_speed))
        return duration, distance

    def execute(self, action: ExecutionAction) -> ExecutionResult:
        dispatch = {
            "reserve": self.reserve,
            "queue": self.queue,
            "order": self.order,
            "delivery": self.delivery,
            "share": self.share,
        }
        handler = dispatch.get(action.action_type)
        if handler is None:
            return ExecutionResult(
                action_type=action.action_type,
                target=action.target,
                status="failed",
                message="未识别的执行动作",
                recovery_hint="请检查 Tool 路由配置。",
                details={"scenario": self.scenario},
            )
        return handler(action)

    def reserve(self, action: ExecutionAction) -> ExecutionResult:
        reference_id = f"MOCK-{abs(hash((action.action_type, action.target))) % 100000:05d}"
        payload_hint = ", ".join(f"{key}={value}" for key, value in action.payload.items())
        if self.scenario == "reserve_timeout" and action.action_type == "reserve":
            return ExecutionResult(
                action_type=action.action_type,
                target=action.target,
                status="failed",
                message="预约接口超时",
                reference_id=reference_id,
                recovery_hint="建议稍后重试，或改约同类型备选活动。",
                details={"scenario": self.scenario},
            )
        message = f"已模拟执行 {action.action_type}，参数: {payload_hint}" if payload_hint else f"已模拟执行 {action.action_type}"
        return ExecutionResult(
            action_type=action.action_type,
            target=action.target,
            status="success",
            message=message,
            reference_id=reference_id,
            details={"scenario": self.scenario},
        )

    def queue(self, action: ExecutionAction) -> ExecutionResult:
        return self._default_action_result(action, fail_when_partial=True, recovery_hint="建议切换到备选餐厅或改为先点单。")

    def order(self, action: ExecutionAction) -> ExecutionResult:
        return self._default_action_result(action)

    def delivery(self, action: ExecutionAction) -> ExecutionResult:
        return self._default_action_result(action, fail_when_partial=True, recovery_hint="建议改为到店自取或取消附加配送。")

    def share(self, action: ExecutionAction) -> ExecutionResult:
        return self._default_action_result(action)

    def _default_action_result(
        self,
        action: ExecutionAction,
        fail_when_partial: bool = False,
        recovery_hint: str = "",
    ) -> ExecutionResult:
        reference_id = f"MOCK-{abs(hash((action.action_type, action.target))) % 100000:05d}"
        payload_hint = ", ".join(f"{key}={value}" for key, value in action.payload.items())
        if self.scenario == "partial_failure" and fail_when_partial:
            return ExecutionResult(
                action_type=action.action_type,
                target=action.target,
                status="failed",
                message=f"{action.action_type} 模拟失败，参数: {payload_hint}" if payload_hint else f"{action.action_type} 模拟失败",
                reference_id=reference_id,
                recovery_hint=recovery_hint,
                details={"scenario": self.scenario},
            )
        message = f"已模拟执行 {action.action_type}，参数: {payload_hint}" if payload_hint else f"已模拟执行 {action.action_type}"
        return ExecutionResult(
            action_type=action.action_type,
            target=action.target,
            status="success",
            message=message,
            reference_id=reference_id,
            details={"scenario": self.scenario},
        )

    def dump_goal(self, goal: Goal) -> dict[str, object]:
        return asdict(goal)

    def data_mode(self) -> str:
        return self.last_data_mode

    def _search_real_candidates(self, goal: Goal, category: str) -> list[Candidate]:
        if not self.amap_service_key:
            return []
        queries = self._build_queries(goal, category)
        results: list[Candidate] = []
        for query in queries:
            pois = self._search_amap(query=query, goal=goal)
            results.extend(self._convert_pois(goal, pois, category, query))
            if len(results) >= 8:
                break
        deduped: list[Candidate] = []
        seen: set[str] = set()
        for candidate in results:
            if candidate.name in seen:
                continue
            deduped.append(candidate)
            seen.add(candidate.name)
        return deduped[:8]

    def _build_queries(self, goal: Goal, category: str) -> list[str]:
        if category == "activity":
            if goal.scene == "family":
                return ["亲子乐园", "儿童乐园", "公园", "手作体验"]
            if goal.scene == "friends":
                return ["保龄球", "展览", "桌游", "城市公园"]
            return ["展览", "公园", "休闲娱乐"]
        if category == "restaurant":
            if "清淡饮食" in goal.dining_preferences:
                return ["轻食", "家常菜", "简餐"]
            if goal.scene == "friends":
                return ["聚餐", "烤肉", "茶餐厅"]
            return ["亲子餐厅", "家常菜", "简餐"]
        if goal.scene == "friends":
            return ["甜品", "咖啡", "桌游"]
        return ["甜品", "咖啡", "散步"]

    def _search_amap(self, query: str, goal: Goal) -> list[dict[str, object]]:
        params: dict[str, object]
        if goal.origin_lat is not None and goal.origin_lng is not None:
            params = {
                "key": self.amap_service_key,
                "location": f"{goal.origin_lng},{goal.origin_lat}",
                "keywords": query,
                "radius": 6000 if goal.distance_preference == "近场" else 12000,
                "offset": 10,
                "page": 1,
                "extensions": "all",
            }
            endpoint = "https://restapi.amap.com/v3/place/around"
        else:
            params = {
                "key": self.amap_service_key,
                "keywords": query,
                "city": goal.city,
                "citylimit": "true" if goal.city else "false",
                "offset": 10,
                "page": 1,
                "extensions": "all",
            }
            endpoint = "https://restapi.amap.com/v3/place/text"
        try:
            with urlopen(f"{endpoint}?{urlencode(params)}", timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []
        if str(payload.get("status")) != "1":
            return []
        return list(payload.get("pois", []))

    def _convert_pois(self, goal: Goal, pois: list[dict[str, object]], category: str, query: str) -> list[Candidate]:
        candidates: list[Candidate] = []
        for poi in pois:
            location = str(poi.get("location", ""))
            lng, lat = self._parse_location(location)
            distance_meters = self._parse_int(poi.get("distance"))
            duration_minutes = self._default_duration(category, goal.scene, query)
            if distance_meters == 0 and goal.origin_lat is not None and goal.origin_lng is not None and lat is not None and lng is not None:
                distance_meters = self._haversine(goal.origin_lat, goal.origin_lng, lat, lng)
            travel_minutes = max(8, math.ceil(distance_meters / (900 if goal.travel_mode == "walking" else 4000) * 60)) if distance_meters else 0
            biz_ext = poi.get("biz_ext", {}) if isinstance(poi.get("biz_ext"), dict) else {}
            rating = self._parse_float(biz_ext.get("rating"), default=4.2)
            price = self._price_level(biz_ext.get("cost"))
            area = str(poi.get("business_area") or poi.get("adname") or poi.get("cityname") or "本地商圈")
            tags = self._build_tags(goal, category, query, str(poi.get("type", "")))
            family_friendly = goal.scene != "friends" or category == "restaurant" or "亲子" in tags or "公园" in query
            reason = self._build_reason(category, query, area, distance_meters)
            candidates.append(
                Candidate(
                    name=str(poi.get("name") or query),
                    category=category,
                    tags=tags,
                    duration_minutes=duration_minutes,
                    area=area,
                    price_level=price,
                    family_friendly=family_friendly,
                    availability="available",
                    address=str(poi.get("address") or area),
                    business_area=area,
                    source="amap",
                    poi_id=str(poi.get("id") or ""),
                    lat=lat,
                    lng=lng,
                    distance_meters=distance_meters,
                    travel_minutes=travel_minutes,
                    score=min(9.3, max(7.0, rating * 1.8)),
                    reason=reason,
                )
            )
        return candidates

    def _build_tags(self, goal: Goal, category: str, query: str, raw_type: str) -> list[str]:
        tags = [query]
        if category == "activity":
            if goal.scene == "family":
                tags.extend(["亲子", "轻松"])
            elif goal.scene == "friends":
                tags.extend(["社交", "朋友局"])
        if category == "restaurant":
            tags.append("需要餐饮安排")
            if "清淡饮食" in goal.dining_preferences:
                tags.append("清淡可选")
            if goal.scene == "friends":
                tags.append("朋友聚餐")
        if category == "addon":
            tags.append("收尾")
        if raw_type:
            tags.append(raw_type.split(";")[0])
        deduped: list[str] = []
        for item in tags:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    def _build_reason(self, category: str, query: str, area: str, distance_meters: int) -> str:
        distance_text = f"距离约 {distance_meters} 米，" if distance_meters else ""
        if category == "restaurant":
            return f"{distance_text}匹配“{query}”餐饮需求，位于{area}。"
        if category == "addon":
            return f"{distance_text}适合作为收尾补充，位于{area}。"
        return f"{distance_text}适合作为主活动候选，位于{area}。"

    def _default_duration(self, category: str, scene: str, query: str) -> int:
        if category == "restaurant":
            return 80 if "简餐" not in query else 70
        if category == "addon":
            return 45 if "散步" not in query else 40
        if scene == "family":
            return 110 if "公园" not in query else 90
        return 120 if "展览" not in query else 100

    def _apply_scenario(self, items: list[Candidate]) -> list[Candidate]:
        if self.scenario == "activity_unavailable":
            for item in items:
                if item.category == "activity":
                    item.availability = "sold_out"
                    break
        if self.scenario == "restaurant_busy":
            for item in items:
                if item.category == "restaurant":
                    item.availability = "queue_45m"
                    break
        if self.scenario == "addon_unavailable":
            for item in items:
                if item.category == "addon":
                    item.availability = "sold_out"
                    break
        return items

    def _fetch_route_minutes(self, origin_lng: float, origin_lat: float, dest_lng: float, dest_lat: float, travel_mode: str) -> tuple[int, int]:
        if not self.amap_service_key:
            return 0, 0
        cache_key = (f"{origin_lng:.6f},{origin_lat:.6f}", f"{dest_lng:.6f},{dest_lat:.6f}", travel_mode)
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]

        endpoint = "https://restapi.amap.com/v3/direction/driving"
        if travel_mode == "walking":
            endpoint = "https://restapi.amap.com/v3/direction/walking"
        params = {
            "key": self.amap_service_key,
            "origin": f"{origin_lng},{origin_lat}",
            "destination": f"{dest_lng},{dest_lat}",
        }
        try:
            with urlopen(f"{endpoint}?{urlencode(params)}", timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return 0, 0

        if str(payload.get("status")) != "1":
            return 0, 0

        route = payload.get("route", {}) if isinstance(payload.get("route"), dict) else {}
        paths = route.get("paths", [])
        if not paths:
            return 0, 0
        first = paths[0]
        duration = max(1, round(self._parse_int(first.get("duration")) / 60))
        distance = self._parse_int(first.get("distance"))
        self._route_cache[cache_key] = (duration, distance)
        return duration, distance

    def _fallback_distance(self, source: Candidate | None, target: Candidate) -> int:
        # 如果两个点都有坐标，用 Haversine 算真实距离
        if source is not None and source.lat is not None and source.lng is not None and target.lat is not None and target.lng is not None:
            return self._haversine(source.lat, source.lng, target.lat, target.lng)
        # 如果目标有坐标但 source 没有（第一段路程），用目标坐标估算
        if source is None and target.lat is not None and target.lng is not None:
            return 3000
        # 如果目标也没有坐标，用北京中心点近似
        if target.lat is not None and target.lng is not None:
            return self._haversine(39.9, 116.4, target.lat, target.lng)
        return 1800 if source is None else 2200

    def _parse_location(self, raw: str) -> tuple[float | None, float | None]:
        try:
            lng, lat = raw.split(",", maxsplit=1)
            return float(lng), float(lat)
        except (AttributeError, ValueError):
            return None, None

    def _parse_int(self, value: object) -> int:
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return 0

    def _parse_float(self, value: object, default: float) -> float:
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return default

    def _price_level(self, value: object) -> str:
        cost = self._parse_int(value)
        if cost <= 0:
            return "medium"
        if cost < 50:
            return "low"
        if cost < 120:
            return "medium"
        return "high"

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> int:
        radius = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return int(radius * c)
