from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.models.dataset import Dataset
from app.schemas.ai import AIInsight, AIInsightNarrative
from app.services.openai_service import request_openai_text
from app.services.schema_profile_service import build_dataset_schema_profile

logger = logging.getLogger(__name__)


def _truncate_items(items: list[str], *, limit: int = 4) -> list[str]:
    return [item for item in items if item.strip()][:limit]


def _column_label(column_name: str | None, fallback: str) -> str:
    if not column_name:
        return fallback
    return column_name.replace("_", " ")


def _build_summary(dataset: Dataset, insights: list[AIInsight]) -> str:
    if not insights:
        return (
            f"The dataset {dataset.name} is available for analysis, but no strong automatic findings were detected "
            "from the current schema and value patterns."
        )

    top_insights = insights[:3]
    if len(top_insights) == 1:
        first = top_insights[0]
        return f"The dataset {dataset.name} is primarily characterized by {first.summary[0].lower() + first.summary[1:] if first.summary else 'one main finding'}."

    first = top_insights[0]
    second = top_insights[1]
    parts = [
        f"The dataset {dataset.name} shows {first.summary.rstrip('.')}.",
        f"It also highlights that {second.summary.rstrip('.').lower()}.",
    ]
    if len(top_insights) > 2:
        parts.append(f"A third relevant signal is that {top_insights[2].summary.rstrip('.').lower()}.")
    return " ".join(parts)


def _build_key_findings(insights: list[AIInsight]) -> list[str]:
    findings: list[str] = []
    for insight in insights:
        findings.append(insight.summary.rstrip(".") + ".")
    return _truncate_items(findings, limit=5)


def _build_risks_or_caveats(
    *,
    dataset: Dataset,
    insights: list[AIInsight],
    profile: list[dict[str, object]],
) -> list[str]:
    caveats: list[str] = []

    constant_columns = [_column_label(str(item.get("display_name")), "column") for item in profile if item.get("semantic_type") == "constant"]
    if constant_columns:
        preview = ", ".join(constant_columns[:3])
        caveats.append(f"Some columns are constant across the dataset, such as {preview}, so they do not add analytical value.")

    low_variance_columns = [_column_label(str(item.get("display_name")), "column") for item in profile if item.get("semantic_type") == "low_variance"]
    if low_variance_columns:
        preview = ", ".join(low_variance_columns[:3])
        caveats.append(f"Low-variance columns such as {preview} may produce weak or trivial patterns.")

    high_cardinality_columns = [
        _column_label(str(item.get("display_name")), "column")
        for item in profile
        if item.get("semantic_type") == "high_cardinality_text"
    ]
    if high_cardinality_columns:
        preview = ", ".join(high_cardinality_columns[:3])
        caveats.append(f"High-cardinality text fields such as {preview} are not ideal for automatic grouping without prior normalization.")

    if getattr(dataset, "row_count", 0) < 20:
        caveats.append("The dataset is small, so some patterns may be unstable and should be validated before making decisions.")

    if insights and all(insight.chart_type == "table" for insight in insights):
        caveats.append("Several findings are represented as tables, which suggests limited chartable structure in the current result set.")

    return _truncate_items(caveats, limit=4)


def _build_recommended_next_questions(insights: list[AIInsight]) -> list[str]:
    questions: list[str] = []
    seen: set[str] = set()

    for insight in insights:
        metric = _column_label(insight.metric, "the main metric")
        dimension = _column_label(insight.dimension, "the leading dimension")
        if insight.type in {"top_performer", "concentration", "comparison"}:
            candidate = f"How does {metric} evolve over time by {dimension}?"
        elif insight.type == "correlation":
            candidate = f"Which segments explain the relationship between {dimension} and {metric}?"
        elif insight.type == "distribution":
            candidate = f"What factors explain the spread observed in {metric}?"
        elif insight.type == "outlier":
            candidate = f"Which records are driving the outliers detected in {metric}?"
        elif insight.type == "trend":
            candidate = f"What explains the change over time in {metric}?"
        else:
            candidate = f"What other dimensions help explain {metric}?"

        if candidate not in seen:
            questions.append(candidate)
            seen.add(candidate)

    if not questions:
        questions.append("How does the main metric evolve over time?")
        questions.append("Which categories explain most of the variation in the dataset?")

    return _truncate_items(questions, limit=4)


def _build_deterministic_narrative(
    *,
    dataset: Dataset,
    insights: list[AIInsight],
    profile: list[dict[str, object]],
) -> AIInsightNarrative:
    return AIInsightNarrative(
        summary=_build_summary(dataset, insights),
        key_findings=_build_key_findings(insights),
        risks_or_caveats=_build_risks_or_caveats(dataset=dataset, insights=insights, profile=profile),
        recommended_next_questions=_build_recommended_next_questions(insights),
    )


def _polish_narrative(narrative: AIInsightNarrative) -> AIInsightNarrative:
    if not settings.openai_api_key:
        return narrative

    try:
        polished_summary = asyncio.run(
            request_openai_text(
                system_prompt=(
                    "You are a BI analyst. Rewrite the provided executive summary as one concise paragraph. "
                    "Preserve the facts. Do not invent findings. Do not use markdown."
                ),
                user_prompt=(
                    f"Summary: {narrative.summary}\n"
                    f"Key findings: {narrative.key_findings}\n"
                    f"Risks: {narrative.risks_or_caveats}"
                ),
                error_prefix="Could not polish insight narrative",
            )
        ).strip()
    except Exception:
        logger.exception("dataset_insight_narrative_polish_failed")
        return narrative

    if polished_summary:
        narrative.summary = polished_summary
    return narrative


def build_insight_narrative(
    *,
    dataset: Dataset,
    insights: list[AIInsight],
    profile: list[dict[str, object]] | None = None,
) -> AIInsightNarrative:
    resolved_profile = profile if profile is not None else build_dataset_schema_profile(dataset)
    narrative = _build_deterministic_narrative(dataset=dataset, insights=insights, profile=resolved_profile)
    return _polish_narrative(narrative)
