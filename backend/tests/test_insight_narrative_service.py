from types import SimpleNamespace

from app.schemas.ai import AIInsight
from app.services import insight_narrative_service


def _dataset(*, row_count: int = 120):
    return SimpleNamespace(
        id=7,
        name="Wildfire",
        description="Wildfire impact dataset",
        row_count=row_count,
        column_count=6,
        columns=[],
    )


def _insights() -> list[AIInsight]:
    return [
        AIInsight(
            type="top_performer",
            title="Bosques leads superficie_afectada",
            summary="Bosques has the highest total superficie_afectada.",
            metric="superficie_afectada",
            dimension="cobertura",
            quality_score=90,
            columns=["category", "metric"],
            rows=[{"category": "Bosques", "metric": 29266}],
        ),
        AIInsight(
            type="correlation",
            title="Positive correlation detected",
            summary="superficie_total and superficie_afectada show a positive correlation of 0.620.",
            metric="superficie_afectada",
            dimension="superficie_total",
            quality_score=88,
            columns=["pair", "correlation"],
            rows=[{"pair": "superficie_total vs superficie_afectada", "correlation": 0.62}],
        ),
        AIInsight(
            type="distribution",
            title="superficie_total distribution snapshot",
            summary="superficie_total ranges from 10.00 to 100.00, with an average of 55.00.",
            metric="superficie_total",
            quality_score=80,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    ]


def test_narrative_is_generated_without_openai(monkeypatch):
    monkeypatch.setattr(insight_narrative_service.settings, "openai_api_key", "")

    narrative = insight_narrative_service.build_insight_narrative(
        dataset=_dataset(),
        insights=_insights(),
        profile=[],
    )

    assert narrative.summary
    assert len(narrative.key_findings) >= 2
    assert any("Bosques has the highest total superficie_afectada." == item for item in narrative.key_findings)


def test_openai_failure_does_not_break_narrative_generation(monkeypatch):
    monkeypatch.setattr(insight_narrative_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        insight_narrative_service,
        "request_openai_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("quota")),
    )

    narrative = insight_narrative_service.build_insight_narrative(
        dataset=_dataset(),
        insights=_insights(),
        profile=[],
    )

    assert narrative.summary
    assert narrative.key_findings


def test_key_findings_are_derived_from_existing_insights(monkeypatch):
    monkeypatch.setattr(insight_narrative_service.settings, "openai_api_key", "")

    insights = _insights()
    narrative = insight_narrative_service.build_insight_narrative(
        dataset=_dataset(),
        insights=insights,
        profile=[],
    )

    expected = {insight.summary.rstrip(".") + "." for insight in insights}
    assert set(narrative.key_findings).issubset(expected)


def test_caveats_appear_for_constant_and_low_variance_columns(monkeypatch):
    monkeypatch.setattr(insight_narrative_service.settings, "openai_api_key", "")
    profile = [
        {"display_name": "fuente", "semantic_type": "constant"},
        {"display_name": "impact_score", "semantic_type": "low_variance"},
    ]

    narrative = insight_narrative_service.build_insight_narrative(
        dataset=_dataset(row_count=10),
        insights=_insights()[:1],
        profile=profile,
    )

    assert any("constant" in caveat.lower() for caveat in narrative.risks_or_caveats)
    assert any("small" in caveat.lower() for caveat in narrative.risks_or_caveats)
