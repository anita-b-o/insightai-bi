from __future__ import annotations

import re
from collections import Counter

from app.schemas.ai import AIInsight, AIInsightRankingMetadata
from app.services.feature_selection_service import FeatureScore


def _normalize_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _text_tokens(value: str | None) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()
    return set(normalized.split(" "))


def _jaccard_similarity(left: str | None, right: str | None) -> float:
    left_tokens = _text_tokens(left)
    right_tokens = _text_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _insight_columns(insight: AIInsight) -> tuple[str, ...]:
    columns = [column.strip().lower() for column in insight.columns if isinstance(column, str) and column.strip()]
    return tuple(sorted(set(columns)))


def _principal_columns(insight: AIInsight) -> tuple[str, ...]:
    columns = []
    if insight.metric:
        columns.append(insight.metric.strip().lower())
    if insight.dimension:
        columns.append(insight.dimension.strip().lower())
    if not columns:
        columns.extend(_insight_columns(insight)[:2])
    return tuple(sorted(set(columns)))


def _dedupe_signature(insight: AIInsight) -> tuple[object, ...]:
    return (
        insight.type.strip().lower(),
        (insight.metric or "").strip().lower(),
        (insight.dimension or "").strip().lower(),
        _insight_columns(insight),
    )


def _deduplication_key(insight: AIInsight) -> str:
    signature = _dedupe_signature(insight)
    return "|".join(str(item) for item in signature)


def _score_components(insight: AIInsight, feature_score_by_column: dict[str, float]) -> tuple[float, float, float, float, float]:
    quality_component = (insight.quality_score / 100.0) * 0.40
    confidence_component = insight.confidence * 0.20
    impact_component = insight.impact * 0.20

    principal_columns = _principal_columns(insight)
    feature_scores = [feature_score_by_column.get(column, 0.0) for column in principal_columns]
    feature_component = ((sum(feature_scores) / len(feature_scores)) if feature_scores else 0.0) * 0.20
    global_score = quality_component + confidence_component + impact_component + feature_component
    return global_score, quality_component, feature_component, impact_component, confidence_component


def deduplicate_insights(insights: list[AIInsight]) -> list[AIInsight]:
    deduplicated: list[AIInsight] = []
    for insight in insights:
        replaced = False
        for index, existing in enumerate(deduplicated):
            same_signature = _dedupe_signature(existing) == _dedupe_signature(insight)
            similar_text = (
                existing.type == insight.type
                and (existing.metric or "") == (insight.metric or "")
                and (existing.dimension or "") == (insight.dimension or "")
                and (
                    _normalize_text(existing.title) == _normalize_text(insight.title)
                    or _normalize_text(existing.summary) == _normalize_text(insight.summary)
                    or _jaccard_similarity(existing.title, insight.title) >= 0.85
                    or _jaccard_similarity(existing.summary, insight.summary) >= 0.85
                )
            )

            if same_signature or similar_text:
                existing_strength = (existing.quality_score, existing.impact, existing.confidence)
                candidate_strength = (insight.quality_score, insight.impact, insight.confidence)
                if candidate_strength > existing_strength:
                    insight.ranking_metadata = insight.ranking_metadata or AIInsightRankingMetadata()
                    insight.ranking_metadata.deduplication_key = _deduplication_key(insight)
                    deduplicated[index] = insight
                else:
                    existing.ranking_metadata = existing.ranking_metadata or AIInsightRankingMetadata()
                    existing.ranking_metadata.deduplication_key = _deduplication_key(existing)
                replaced = True
                break

        if not replaced:
            insight.ranking_metadata = insight.ranking_metadata or AIInsightRankingMetadata()
            insight.ranking_metadata.deduplication_key = _deduplication_key(insight)
            deduplicated.append(insight)

    return deduplicated


def rank_insights(insights: list[AIInsight], feature_scores: list[FeatureScore]) -> list[AIInsight]:
    feature_score_by_column = {item.column.strip().lower(): item.final_score for item in feature_scores}
    for insight in insights:
        global_score, quality_component, feature_component, impact_component, confidence_component = _score_components(
            insight,
            feature_score_by_column,
        )
        metadata = insight.ranking_metadata or AIInsightRankingMetadata()
        metadata.global_score = max(0.0, min(1.0, global_score))
        metadata.quality_component = max(0.0, min(1.0, quality_component))
        metadata.feature_importance_component = max(0.0, min(1.0, feature_component))
        metadata.impact_component = max(0.0, min(1.0, impact_component))
        metadata.confidence_component = max(0.0, min(1.0, confidence_component))
        metadata.deduplication_key = metadata.deduplication_key or _deduplication_key(insight)
        insight.ranking_metadata = metadata

    return sorted(
        insights,
        key=lambda insight: (
            insight.ranking_metadata.global_score if insight.ranking_metadata and insight.ranking_metadata.global_score is not None else 0.0,
            insight.impact,
            insight.confidence,
            insight.quality_score,
        ),
        reverse=True,
    )


def select_top_insights(insights: list[AIInsight], limit: int = 6) -> list[AIInsight]:
    if limit <= 0:
        return []

    selected: list[AIInsight] = []
    remaining = list(insights)

    while remaining and len(selected) < limit:
        type_counts = Counter(item.type for item in selected)
        column_counts = Counter(column for item in selected for column in _principal_columns(item))

        best_index = 0
        best_score = float("-inf")
        best_penalty = 0.0
        for index, insight in enumerate(remaining):
            diversity_penalty = (type_counts[insight.type] * 0.12)
            diversity_penalty += sum(column_counts[column] * 0.08 for column in _principal_columns(insight))
            base_score = insight.ranking_metadata.global_score if insight.ranking_metadata and insight.ranking_metadata.global_score is not None else 0.0
            adjusted_score = base_score - diversity_penalty
            if adjusted_score > best_score:
                best_score = adjusted_score
                best_index = index
                best_penalty = diversity_penalty

        chosen = remaining.pop(best_index)
        metadata = chosen.ranking_metadata or AIInsightRankingMetadata()
        metadata.diversity_penalty = max(0.0, best_penalty)
        metadata.selected_reason = (
            f"Selected for high global score and diversity across type {chosen.type}"
            if metadata.global_score is not None
            else f"Selected for diversity across type {chosen.type}"
        )
        chosen.ranking_metadata = metadata
        selected.append(chosen)

    return selected
