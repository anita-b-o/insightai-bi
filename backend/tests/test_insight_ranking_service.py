from app.schemas.ai import AIInsight
from app.services.feature_selection_service import FeatureScore
from app.services.insight_ranking_service import deduplicate_insights, rank_insights, select_top_insights


def _feature(column: str, score: float) -> FeatureScore:
    return FeatureScore(
        column=column,
        semantic_type="metric",
        variance=score,
        correlation_strength=score,
        entropy=0.0,
        cardinality=score,
        non_null_ratio=1.0,
        outlier_score=0.0,
        final_score=score,
    )


def _insight(
    *,
    insight_type: str,
    title: str,
    metric: str | None,
    dimension: str | None,
    quality_score: int,
    confidence: float = 0.8,
    impact: float = 0.8,
    summary: str | None = None,
) -> AIInsight:
    return AIInsight(
        type=insight_type,
        title=title,
        summary=summary or title,
        metric=metric,
        dimension=dimension,
        quality_score=quality_score,
        confidence=confidence,
        impact=impact,
        columns=[item for item in [metric, dimension] if item],
        rows=[{"value": 1}],
    )


def test_deduplicate_insights_removes_exact_duplicates():
    first = _insight(insight_type="distribution", title="Revenue distribution", metric="revenue", dimension=None, quality_score=70)
    second = _insight(insight_type="distribution", title="Revenue distribution", metric="revenue", dimension=None, quality_score=90)

    deduplicated = deduplicate_insights([first, second])

    assert len(deduplicated) == 1
    assert deduplicated[0].quality_score == 90


def test_rank_insights_prioritizes_important_features():
    low = _insight(insight_type="distribution", title="Metric A distribution", metric="metric_a", dimension=None, quality_score=85)
    high = _insight(insight_type="distribution", title="Metric B distribution", metric="metric_b", dimension=None, quality_score=85)

    ranked = rank_insights([low, high], [_feature("metric_a", 0.2), _feature("metric_b", 0.9)])

    assert ranked[0].metric == "metric_b"
    assert ranked[0].ranking_metadata is not None
    assert ranked[0].ranking_metadata.global_score is not None
    assert 0.0 <= ranked[0].ranking_metadata.global_score <= 1.0


def test_select_top_insights_preserves_type_diversity():
    top_a = _insight(insight_type="distribution", title="A", metric="revenue", dimension=None, quality_score=95)
    top_b = _insight(insight_type="distribution", title="B", metric="profit", dimension=None, quality_score=94)
    top_c = _insight(insight_type="correlation", title="C", metric="revenue", dimension="orders", quality_score=93)

    selected = select_top_insights([top_a, top_b, top_c], limit=2)

    assert len(selected) == 2
    assert {item.type for item in selected} == {"distribution", "correlation"}
    assert all(item.ranking_metadata is not None for item in selected)
    assert all(item.ranking_metadata.selected_reason for item in selected)


def test_select_top_insights_penalizes_repeated_primary_columns():
    repeated_first = _insight(insight_type="top_performer", title="Revenue by channel", metric="revenue", dimension="channel", quality_score=92)
    repeated_second = _insight(insight_type="distribution", title="Revenue distribution", metric="revenue", dimension=None, quality_score=91)
    diverse = _insight(insight_type="outlier", title="Profit outliers", metric="profit", dimension="store", quality_score=90)

    selected = select_top_insights([repeated_first, repeated_second, diverse], limit=2)

    assert len(selected) == 2
    assert any(item.metric == "profit" for item in selected)


def test_select_top_insights_limits_to_top_n():
    insights = [
        _insight(insight_type="distribution", title=f"Insight {index}", metric=f"metric_{index}", dimension=None, quality_score=90 - index)
        for index in range(8)
    ]

    selected = select_top_insights(insights, limit=6)

    assert len(selected) == 6


def test_deduplicate_insights_sets_deduplication_key():
    insight = _insight(insight_type="distribution", title="Revenue distribution", metric="revenue", dimension=None, quality_score=70)

    deduplicated = deduplicate_insights([insight])

    assert deduplicated[0].ranking_metadata is not None
    assert deduplicated[0].ranking_metadata.deduplication_key


def test_ranking_metadata_fallback_allows_missing_metadata():
    insight = _insight(insight_type="distribution", title="Revenue distribution", metric="revenue", dimension=None, quality_score=70)
    insight.ranking_metadata = None

    selected = select_top_insights([insight], limit=1)

    assert len(selected) == 1
    assert selected[0].ranking_metadata is not None
    assert selected[0].ranking_metadata.selected_reason
