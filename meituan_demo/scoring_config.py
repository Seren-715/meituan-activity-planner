"""评分权重配置。

所有评分相关的魔法数字集中管理，便于答辩时解释"为什么是这个值"，
也方便后续通过 A/B 实验或配置文件调整。

权重设计依据：
- 候选评分：基础质量 * 8，让原始评分（0-10）映射到 0-80 分区间
- 场景匹配 +10：场景适配是筛选的第一优先级
- 距离匹配 +8：近场偏好用户对距离敏感度仅次于场景
- 通勤衰减：travel_minutes / 3，每多 3 分钟通勤扣 1 分
- 步行惩罚 -6：步行 > 20 分钟体验显著下降
- 节奏/饮食/室内 +5~6：细分偏好加成，权重低于场景和距离
- 低龄亲子 +4：带幼儿时室内亲子是强加分
- 餐饮需求 +4：有餐饮安排需求时餐饮候选加分

评分维度（满分 100）：
- 路线效率（25）：总时长越接近目标越好
- 人群适配（25）：场景 + 偏好匹配度
- 体验丰富（20）：候选质量 + 是否有补充活动
- 性价比（15）：质量与成本的平衡
- 执行稳定性（15）：距离、节奏、排队提醒
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateScoringWeights:
    """候选打分阶段的权重。"""
    base_quality_multiplier: float = 8.0
    scene_match_bonus: float = 10.0
    distance_nearby_bonus: float = 8.0
    travel_decay_divisor: float = 3.0
    travel_decay_max: float = 10.0
    walking_nearby_bonus: float = 5.0
    walking_far_penalty: float = 6.0
    walking_far_threshold: int = 20
    pace_bonus: float = 6.0
    diet_bonus: float = 6.0
    indoor_bonus: float = 5.0
    parking_bonus: float = 2.0
    young_child_bonus: float = 4.0
    young_child_age_threshold: int = 6
    dining_demand_bonus: float = 4.0


@dataclass(frozen=True)
class ItineraryScoringWeights:
    """方案评分维度的权重配置。"""
    # 路线效率
    route_efficiency_max: float = 25.0
    route_efficiency_min: float = 8.0
    route_efficiency_decay: float = 8.0

    # 人群适配
    scene_fit_max: float = 25.0
    scene_fit_base: float = 10.0
    scene_fit_multiplier: float = 1.5

    # 体验丰富
    experience_max: float = 20.0
    experience_quality_multiplier: float = 1.8
    experience_addon_bonus: float = 4.0
    experience_default_addon_score: float = 7.2

    # 性价比
    cost_max: float = 15.0
    cost_base: float = 7.0
    cost_multiplier: float = 0.9

    # 执行稳定性
    stability_max: float = 15.0
    stability_base: float = 6.0
    alert_penalty: float = 1.5
    stability_min: float = 6.0


@dataclass(frozen=True)
class ItineraryLimits:
    """方案时长限制（分钟）。"""
    min_total_minutes: int = 210
    max_total_minutes: int = 390


@dataclass(frozen=True)
class FallbackItineraryWeights:
    """资源不足时的降级方案评分。"""
    route_efficiency: float = 16.0
    scene_fit: float = 17.0
    experience: float = 13.0
    cost_effectiveness: float = 14.0
    execution_stability: float = 12.0
    total_score: float = 72.0


# 默认配置实例
CANDIDATE_WEIGHTS = CandidateScoringWeights()
ITINERARY_WEIGHTS = ItineraryScoringWeights()
ITINERARY_LIMITS = ItineraryLimits()
FALLBACK_WEIGHTS = FallbackItineraryWeights()
