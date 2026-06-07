from __future__ import annotations

from itertools import product
import re

from .mock_tools import MockToolbox
from .models import Candidate, ExecutionAction, Goal, Itinerary, ItineraryStop, PlanningOutput, ScoreBreakdownItem
from .scoring_config import CANDIDATE_WEIGHTS, ITINERARY_WEIGHTS, ITINERARY_LIMITS, FALLBACK_WEIGHTS


class Planner:
    NEARBY_AREAS = {"社区商圈", "近场公园", "同商圈"}

    def __init__(self, toolbox: MockToolbox) -> None:
        self.toolbox = toolbox

    def build_plan(self, goal: Goal) -> PlanningOutput:
        activities = self._rank_candidates(self.toolbox.search_activities(goal), goal)
        restaurants = self._rank_candidates(self.toolbox.search_restaurants(goal), goal)
        addons = self._rank_candidates(self.toolbox.search_addons(goal), goal)

        itineraries = self._build_itineraries(goal, activities, restaurants, addons)
        primary = itineraries[0]
        alternatives = itineraries[1:3]
        primary.fallback_options = [self._summarize_itinerary(item) for item in alternatives]
        recommendation_reason = self._recommendation_reason(primary, alternatives)
        primary.recommendation_reason = recommendation_reason

        actions = self._build_actions(goal, primary)
        alternative_actions = [self._build_actions(goal, item) for item in alternatives]
        return PlanningOutput(
            goal=goal,
            itinerary=primary,
            actions=actions,
            alternatives=alternatives,
            alternative_actions=alternative_actions,
            data_mode=self.toolbox.data_mode(),
            recommendation_reason=recommendation_reason,
        )

    def _rank_candidates(self, candidates: list[Candidate], goal: Goal) -> list[Candidate]:
        filtered = [candidate for candidate in candidates if self._hard_filter(candidate, goal)]
        if goal.distance_preference == "近场":
            nearby = [candidate for candidate in filtered if candidate.area in self.NEARBY_AREAS]
            if nearby:
                filtered = nearby
        if not filtered:
            filtered = candidates[:]

        return sorted(filtered, key=lambda item: self._candidate_score(item, goal), reverse=True)[:4]

    def _build_itineraries(
        self,
        goal: Goal,
        activities: list[Candidate],
        restaurants: list[Candidate],
        addons: list[Candidate],
    ) -> list[Itinerary]:
        plans: list[Itinerary] = []
        seen: set[tuple[str, str, str]] = set()

        for activity, restaurant, addon in product(activities[:3], restaurants[:3], [None] + addons[:3]):
            key = (activity.name, restaurant.name, addon.name if addon else "")
            if key in seen:
                continue
            seen.add(key)

            itinerary = self._assemble_itinerary(goal, activity, restaurant, addon)
            if itinerary is not None:
                plans.append(itinerary)

        if plans:
            return sorted(plans, key=lambda item: item.score, reverse=True)

        fallback = self._assemble_itinerary(goal, activities[0], restaurants[0], addons[0] if addons else None)
        if fallback is None:
            fallback = self._build_minimal_itinerary(goal, activities[0], restaurants[0])
        return [fallback]

    def _assemble_itinerary(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> Itinerary | None:
        activity_ok, activity_message = self.toolbox.check_availability(activity)
        restaurant_ok, restaurant_message = self.toolbox.check_availability(restaurant)
        if not activity_ok or not restaurant_ok:
            return None

        addon_message = ""
        if addon is not None:
            addon_ok, addon_message = self.toolbox.check_availability(addon)
            if not addon_ok:
                addon = None

        transition_one, distance_one = self.toolbox.estimate_transition(goal, None, activity)
        transition_two, distance_two = self.toolbox.estimate_transition(goal, activity, restaurant)
        transition_three, distance_three = self.toolbox.estimate_transition(goal, restaurant, addon) if addon else (20, 0)
        total_minutes = activity.duration_minutes + restaurant.duration_minutes + transition_one + transition_two + transition_three
        if addon is not None:
            total_minutes += addon.duration_minutes

        if total_minutes < ITINERARY_LIMITS.min_total_minutes or total_minutes > ITINERARY_LIMITS.max_total_minutes:
            return None

        alerts = self._collect_alerts(activity_message, restaurant_message, addon_message)
        route_summary = [
            self._route_text(goal.origin_name or "出发点", activity, transition_one, distance_one),
            self._route_text(activity.name, restaurant, transition_two, distance_two),
        ]
        if addon is not None:
            route_summary.append(self._route_text(restaurant.name, addon, transition_three, distance_three))
        stops = self._build_stops(
            goal,
            activity,
            restaurant,
            addon,
            activity_message,
            restaurant_message,
            addon_message,
            transition_one,
            distance_one,
            transition_two,
            distance_two,
            transition_three,
            distance_three,
        )
        score_breakdown = self._score_breakdown(goal, activity, restaurant, addon, total_minutes, alerts)
        score = sum(item.score for item in score_breakdown)
        planning_basis = self._planning_basis(goal, activity, restaurant, addon)
        rationale = [
            f"总时长约 {total_minutes} 分钟，贴近 {goal.duration_hours} 小时目标。",
            f"优先兼顾 {self._scene_text(goal)} 与{goal.distance_preference}路线。",
            "主活动、餐饮、补充活动按衔接顺序评分，并用统一标准对比主备方案。",
        ]

        return Itinerary(
            title=self._build_title(goal),
            total_minutes=total_minutes,
            stops=stops,
            rationale=rationale,
            score=round(score, 1),
            total_travel_minutes=transition_one + transition_two + transition_three,
            route_summary=route_summary,
            map_center_lat=self._center_lat([activity, restaurant, addon]),
            map_center_lng=self._center_lng([activity, restaurant, addon]),
            alerts=alerts,
            score_breakdown=score_breakdown,
            recommendation_reason=self._itinerary_reason(goal, activity, restaurant, addon),
            planning_basis=planning_basis,
        )

    def _build_minimal_itinerary(self, goal: Goal, activity: Candidate, restaurant: Candidate) -> Itinerary:
        start_leg, start_distance = self.toolbox.estimate_transition(goal, None, activity)
        second_leg, second_distance = self.toolbox.estimate_transition(goal, activity, restaurant)
        total_minutes = activity.duration_minutes + restaurant.duration_minutes + start_leg + second_leg + 20
        stops = self._build_stops(
            goal,
            activity,
            restaurant,
            None,
            "资源可用",
            "资源可用",
            "",
            start_leg,
            start_distance,
            second_leg,
            second_distance,
            20,
            0,
        )
        return Itinerary(
            title=self._build_title(goal),
            total_minutes=total_minutes,
            stops=stops,
            rationale=["当前可用资源较少，先给出活动加餐饮的基础闭环方案。"],
            score=FALLBACK_WEIGHTS.total_score,
            total_travel_minutes=start_leg + second_leg + 20,
            route_summary=[
                self._route_text(goal.origin_name or "出发点", activity, start_leg, start_distance),
                self._route_text(activity.name, restaurant, second_leg, second_distance),
            ],
            map_center_lat=self._center_lat([activity, restaurant]),
            map_center_lng=self._center_lng([activity, restaurant]),
            alerts=["补充活动候选不足，建议执行前再确认是否追加收尾安排。"],
            score_breakdown=[
                ScoreBreakdownItem(label="路线效率", score=FALLBACK_WEIGHTS.route_efficiency, detail="当前为基础闭环方案，优先保证路程和时长可落地。"),
                ScoreBreakdownItem(label="人群适配", score=FALLBACK_WEIGHTS.scene_fit, detail="主活动和餐饮仍围绕当前人群需求筛选。"),
                ScoreBreakdownItem(label="体验丰富", score=FALLBACK_WEIGHTS.experience, detail="因补充活动缺失，丰富度略低于完整方案。"),
                ScoreBreakdownItem(label="性价比", score=FALLBACK_WEIGHTS.cost_effectiveness, detail="保留活动+餐饮核心链路，避免因资源不足完全失效。"),
                ScoreBreakdownItem(label="执行稳定性", score=FALLBACK_WEIGHTS.execution_stability, detail="优先保留当前可确认的关键资源。"),
            ],
            recommendation_reason="当前资源不足时，这条基础闭环更稳，适合先锁定主活动和餐饮。",
            planning_basis=self._planning_basis(goal, activity, restaurant, None),
        )

    def _build_stops(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
        activity_message: str,
        restaurant_message: str,
        addon_message: str,
        start_leg_minutes: int,
        start_leg_distance: int,
        second_leg_minutes: int,
        second_leg_distance: int,
        third_leg_minutes: int,
        third_leg_distance: int,
    ) -> list[ItineraryStop]:
        current_minutes = self._start_hour(goal.time_window) * 60 + start_leg_minutes
        stops = [
            ItineraryStop(
                start_time=self._format_minutes(current_minutes),
                duration_minutes=activity.duration_minutes,
                title=activity.name,
                category=activity.category,
                location=activity.area,
                note=f"{activity.reason} {activity_message}".strip(),
                address=activity.address,
                business_area=activity.business_area,
                source=activity.source,
                lat=activity.lat,
                lng=activity.lng,
                distance_from_prev_meters=start_leg_distance,
                travel_minutes_from_prev=start_leg_minutes,
            )
        ]

        current_minutes += activity.duration_minutes + second_leg_minutes
        stops.append(
            ItineraryStop(
                start_time=self._format_minutes(current_minutes),
                duration_minutes=restaurant.duration_minutes,
                title=restaurant.name,
                category=restaurant.category,
                location=restaurant.area,
                note=f"{restaurant.reason} {restaurant_message}".strip(),
                address=restaurant.address,
                business_area=restaurant.business_area,
                source=restaurant.source,
                lat=restaurant.lat,
                lng=restaurant.lng,
                distance_from_prev_meters=second_leg_distance,
                travel_minutes_from_prev=second_leg_minutes,
            )
        )

        if addon is not None:
            current_minutes += restaurant.duration_minutes + third_leg_minutes
            stops.append(
                ItineraryStop(
                    start_time=self._format_minutes(current_minutes),
                    duration_minutes=addon.duration_minutes,
                    title=addon.name,
                    category=addon.category,
                    location=addon.area,
                    note=f"{addon.reason} {addon_message}".strip(),
                    address=addon.address,
                    business_area=addon.business_area,
                    source=addon.source,
                    lat=addon.lat,
                    lng=addon.lng,
                    distance_from_prev_meters=third_leg_distance,
                    travel_minutes_from_prev=third_leg_minutes,
                )
            )

        return stops

    def _build_actions(self, goal: Goal, itinerary: Itinerary) -> list[ExecutionAction]:
        activity_stop = next(stop for stop in itinerary.stops if stop.category == "activity")
        restaurant_stop = next(stop for stop in itinerary.stops if stop.category == "restaurant")
        actions = [
            ExecutionAction(
                action_type="reserve",
                target=activity_stop.title,
                payload={"time_window": goal.time_window, "group_size": str(goal.group_size)},
            ),
            ExecutionAction(
                action_type="queue",
                target=restaurant_stop.title,
                payload={"group_size": str(goal.group_size), "scene": goal.scene},
            ),
        ]
        if goal.scene == "family":
            actions.append(
                ExecutionAction(
                    action_type="delivery",
                    target="餐后蛋糕配送到餐厅",
                    payload={"restaurant": restaurant_stop.title, "scene": goal.scene},
                )
            )
        else:
            actions.append(
                ExecutionAction(
                    action_type="order",
                    target="聚会饮品预点单",
                    payload={"restaurant": restaurant_stop.title, "scene": goal.scene},
                )
            )
        actions.append(
            ExecutionAction(
                action_type="share",
                target=goal.share_target,
                payload={"scene": goal.scene, "itinerary_score": f"{itinerary.score:.1f}"},
            )
        )
        return actions

    def _hard_filter(self, candidate: Candidate, goal: Goal) -> bool:
        tags = set(candidate.tags)
        if goal.scene == "family" and not candidate.family_friendly:
            return False
        if goal.scene == "friends" and candidate.category == "activity" and "亲子" in tags and "社交" not in tags:
            return False
        if goal.scene == "friends" and candidate.category == "restaurant" and "亲子座椅" in tags and "朋友聚餐" not in tags:
            return False
        if "清淡饮食" in goal.dining_preferences and candidate.category == "restaurant" and "重口味" in tags:
            return False
        if "室内优先" in goal.special_needs and candidate.category == "activity" and not ({"室内", "雨天可行"} & tags):
            return False
        if goal.travel_mode == "walking" and candidate.travel_minutes and candidate.travel_minutes > 25:
            return False
        if goal.scene == "family" and self._child_age_num(goal) is not None and self._child_age_num(goal) <= 6:
            if candidate.category == "restaurant" and ("重口味" in tags or any(token in candidate.name for token in ["火锅", "烤肉", "烧烤"])):
                return False
        if goal.pace_preference == "轻松" and candidate.category == "activity" and "互动" in tags and candidate.area == "核心商圈":
            return False
        return True

    def _candidate_score(self, candidate: Candidate, goal: Goal) -> float:
        w = CANDIDATE_WEIGHTS
        score = candidate.score * w.base_quality_multiplier
        tags = set(candidate.tags)

        if goal.scene == "family" and candidate.family_friendly:
            score += w.scene_match_bonus
        if goal.scene == "friends" and ("社交" in tags or "朋友局" in tags or "聊天" in tags):
            score += w.scene_match_bonus
        if goal.distance_preference == "近场" and candidate.area in self.NEARBY_AREAS:
            score += w.distance_nearby_bonus
        if candidate.travel_minutes:
            score += max(0.0, w.travel_decay_max - candidate.travel_minutes / w.travel_decay_divisor)
        if goal.travel_mode == "walking":
            if candidate.area in self.NEARBY_AREAS:
                score += w.walking_nearby_bonus
            if candidate.travel_minutes and candidate.travel_minutes > w.walking_far_threshold:
                score -= w.walking_far_penalty
        if goal.pace_preference == "轻松" and {"低折腾", "轻松", "散步", "快捷"} & tags:
            score += w.pace_bonus
        if "清淡饮食" in goal.dining_preferences and {"清淡可选", "轻食"} & tags:
            score += w.diet_bonus
        if "室内优先" in goal.special_needs and {"室内", "雨天可行"} & tags:
            score += w.indoor_bonus
        if "停车方便" in goal.special_needs and candidate.area in self.NEARBY_AREAS:
            score += w.parking_bonus
        if goal.scene == "family" and self._child_age_num(goal) is not None and self._child_age_num(goal) <= w.young_child_age_threshold:
            if candidate.category == "activity" and {"室内", "亲子"} & tags:
                score += w.young_child_bonus
        if "需要餐饮安排" in goal.preferences and candidate.category == "restaurant":
            score += w.dining_demand_bonus

        _, availability_message = self.toolbox.check_availability(candidate)
        if "等待" in availability_message:
            score -= 3
        return score

    def _score_breakdown(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
        total_minutes: int,
        alerts: list[str],
    ) -> list[ScoreBreakdownItem]:
        w = ITINERARY_WEIGHTS
        target_minutes = goal.duration_hours * 60
        average_quality = (activity.score + restaurant.score + (addon.score if addon else w.experience_default_addon_score)) / 3
        route_efficiency = max(w.route_efficiency_min, w.route_efficiency_max - abs(total_minutes - target_minutes) / w.route_efficiency_decay)
        scene_fit = min(w.scene_fit_max, w.scene_fit_base + self._scene_bundle_score(goal, activity, restaurant, addon) * w.scene_fit_multiplier)
        experience = min(w.experience_max, average_quality * w.experience_quality_multiplier + (w.experience_addon_bonus if addon is not None else 0.0))
        cost_effectiveness = min(w.cost_max, w.cost_base + average_quality * w.cost_multiplier)
        execution_stability = min(
            w.stability_max,
            w.stability_base + self._distance_bundle_score(goal, activity, restaurant, addon) + self._pace_bundle_score(goal, activity, restaurant, addon) - len(alerts) * w.alert_penalty,
        )
        return [
            ScoreBreakdownItem(
                label="路线效率",
                score=round(route_efficiency, 1),
                detail=f"总时长 {total_minutes} 分钟，目标约 {goal.duration_hours} 小时，路线按顺路衔接优先。",
            ),
            ScoreBreakdownItem(
                label="人群适配",
                score=round(scene_fit, 1),
                detail=f"围绕{self._scene_text(goal)}筛选主活动与餐饮，并考虑特殊需求与节奏。",
            ),
            ScoreBreakdownItem(
                label="体验丰富",
                score=round(experience, 1),
                detail="组合了主活动、餐饮和可选收尾，避免只有单点推荐。",
            ),
            ScoreBreakdownItem(
                label="性价比",
                score=round(cost_effectiveness, 1),
                detail="优先选择时长和体验密度更平衡的组合，而不是堆砌点位。",
            ),
            ScoreBreakdownItem(
                label="执行稳定性",
                score=round(max(w.stability_min, execution_stability), 1),
                detail="会参考距离、排队提醒和资源可用性，优先保留更稳妥的方案。",
            ),
        ]

    def _distance_bundle_score(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> float:
        if goal.distance_preference != "近场":
            return 6.0
        score = 0.0
        for candidate in [activity, restaurant, addon]:
            if candidate is None:
                continue
            if candidate.travel_minutes:
                score += max(1.0, 4.0 - candidate.travel_minutes / 15)
            else:
                score += 3.0 if candidate.area in self.NEARBY_AREAS else 1.0
        return score

    def _scene_bundle_score(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> float:
        score = 5.0
        if goal.scene == "family":
            score += 3.0 if activity.family_friendly and restaurant.family_friendly else 0.0
            if goal.child_age_hint and "室内" in activity.tags:
                score += 2.0
        if goal.scene == "friends":
            tags = set(activity.tags + restaurant.tags + (addon.tags if addon else []))
            if {"社交", "朋友局", "聊天"} & tags:
                score += 4.0
        return score

    def _child_age_num(self, goal: Goal) -> int | None:
        if not goal.child_age_hint:
            return None
        match = re.search(r"\d+", goal.child_age_hint)
        if not match:
            return None
        return int(match.group())

    def _pace_bundle_score(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> float:
        if goal.pace_preference != "轻松":
            return 5.0
        tags = set(activity.tags + restaurant.tags + (addon.tags if addon else []))
        score = 4.0
        if {"低折腾", "轻松", "散步", "快捷"} & tags:
            score += 2.0
        if activity.area in self.NEARBY_AREAS and restaurant.area in self.NEARBY_AREAS:
            score += 2.0
        return score

    def _collect_alerts(self, *messages: str) -> list[str]:
        return [message for message in messages if "等待" in message]

    def _start_hour(self, time_window: str) -> int:
        mapping = {"上午": 10, "中午": 12, "下午": 14, "晚上": 18}
        return mapping.get(time_window, 14)

    def _build_title(self, goal: Goal) -> str:
        prefix = {
            "family": "家庭轻松半日方案",
            "friends": "朋友聚会半日方案",
            "generic": "本地短时活动方案",
        }
        return prefix.get(goal.scene, "本地短时活动方案")

    def _transition_minutes(self, source_area: str, target_area: str) -> int:
        if source_area == target_area:
            return 15
        pair = {source_area, target_area}
        if pair <= self.NEARBY_AREAS:
            return 20
        if "核心商圈" in pair or "次核心商圈" in pair:
            return 30
        return 25

    def _format_minutes(self, total_minutes: int) -> str:
        hour = total_minutes // 60
        minute = total_minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def _scene_text(self, goal: Goal) -> str:
        return {"family": "家庭出行", "friends": "朋友聚会"}.get(goal.scene, "本地短时出行")

    def _summarize_itinerary(self, itinerary: Itinerary) -> str:
        stop_names = " -> ".join(stop.title for stop in itinerary.stops)
        return f"{stop_names}（{itinerary.total_minutes} 分钟，评分 {itinerary.score:.1f}）"

    def _planning_basis(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> list[str]:
        basis = [
            "先抽取人群、时段、距离、节奏、饮食等约束，再进入候选筛选。",
            "先定主活动，再找同线路餐饮和收尾活动，尽量避免回头路。",
            "主备方案使用同一评分标准，保证推荐理由可解释、可对比。",
        ]
        if goal.scene == "family":
            basis.append("家庭场景优先低折腾、亲子友好、清淡可选与天气稳定性。")
        elif goal.scene == "friends":
            basis.append("朋友场景优先社交氛围、聊天便利度和多人执行成功率。")
        if goal.travel_mode == "walking":
            basis.append("步行模式会进一步压缩候选半径，优先近场商圈。")
        if addon is None:
            basis.append("当前候选里未加入补充活动时，会优先保证活动加餐饮的基础闭环。")
        basis.append(f"当前主活动候选是“{activity.name}”，餐饮候选是“{restaurant.name}”。")
        return basis

    def _itinerary_reason(
        self,
        goal: Goal,
        activity: Candidate,
        restaurant: Candidate,
        addon: Candidate | None,
    ) -> str:
        addon_text = f"，再用 {addon.name} 做收尾" if addon is not None else ""
        return (
            f"这条方案先用 {activity.name} 承接{self._scene_text(goal)}的核心诉求，"
            f"再衔接 {restaurant.name} 控制通勤和用餐节奏{addon_text}，"
            f"整体更像一条顺路、可执行的下午安排。"
        )

    def _recommendation_reason(self, primary: Itinerary, alternatives: list[Itinerary]) -> str:
        if not alternatives:
            return primary.recommendation_reason or "当前候选较少，这条方案是最稳妥的完整闭环。"
        runner_up = alternatives[0]
        score_gap = round(primary.score - runner_up.score, 1)
        top_primary = max(primary.score_breakdown, key=lambda item: item.score) if primary.score_breakdown else None
        top_alt = max(runner_up.score_breakdown, key=lambda item: item.score) if runner_up.score_breakdown else None
        if top_primary and top_alt and top_primary.label != top_alt.label:
            return (
                f"推荐主方案，因为它在“{top_primary.label}”上的表现更突出，"
                f"相比备选领先 {score_gap} 分，更适合作为优先执行版本。"
            )
        return (
            f"推荐主方案，因为它在统一评分下领先备选 {score_gap} 分，"
            "路线衔接和执行稳定性更均衡。"
        )

    def _center_lat(self, candidates: list[Candidate | None]) -> float | None:
        values = [candidate.lat for candidate in candidates if candidate is not None and candidate.lat is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 6)

    def _center_lng(self, candidates: list[Candidate | None]) -> float | None:
        values = [candidate.lng for candidate in candidates if candidate is not None and candidate.lng is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 6)

    def _route_text(self, source_name: str, target: Candidate, minutes: int, distance: int) -> str:
        distance_text = f"{distance} 米" if distance else "未知距离"
        return f"{source_name} -> {target.name}：约 {minutes} 分钟，{distance_text}"
