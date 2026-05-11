from app.services.column_semantic_service import classify_column_semantics


def test_classify_identifier_column():
    profile = classify_column_semantics(
        column_name="customer_id",
        inferred_type="integer",
        distinct_count=200,
        sample_values=[101, 102],
        row_count=200,
    )

    assert profile == {
        "column": "customer_id",
        "semantic_type": "identifier",
        "is_metric": False,
        "is_dimension": False,
        "usable_for_correlation": False,
        "usable_for_grouping": False,
    }


def test_classify_foreign_key_identifier_column():
    profile = classify_column_semantics(
        column_name="provincia_id",
        inferred_type="integer",
        distinct_count=24,
        sample_values=[1, 2],
        row_count=100,
    )

    assert profile["semantic_type"] == "identifier"
    assert profile["usable_for_correlation"] is False


def test_classify_constant_column():
    profile = classify_column_semantics(
        column_name="source",
        inferred_type="string",
        distinct_count=1,
        sample_values=["IGN"],
        row_count=100,
    )

    assert profile["semantic_type"] == "constant"
    assert profile["usable_for_grouping"] is False


def test_classify_temporal_column_from_sample():
    profile = classify_column_semantics(
        column_name="created_at",
        inferred_type="string",
        distinct_count=25,
        sample_values=["2026-04-30"],
        row_count=100,
    )

    assert profile["semantic_type"] == "temporal"
    assert profile["is_dimension"] is True
    assert profile["usable_for_grouping"] is True


def test_classify_geographic_latitude_column():
    profile = classify_column_semantics(
        column_name="centroide_lat",
        inferred_type="float",
        distinct_count=40,
        sample_values=[-34.6037, -33.4489],
        row_count=100,
    )

    assert profile["semantic_type"] == "geographic_lat"
    assert profile["is_metric"] is False
    assert profile["usable_for_correlation"] is False


def test_classify_numeric_metric_column():
    profile = classify_column_semantics(
        column_name="superficie_total",
        inferred_type="float",
        distinct_count=90,
        sample_values=[100.5, 120.0, 130.25],
        row_count=100,
    )

    assert profile["semantic_type"] == "metric"
    assert profile["is_metric"] is True
    assert profile["usable_for_correlation"] is True


def test_classify_high_cardinality_text_column():
    profile = classify_column_semantics(
        column_name="review_text",
        inferred_type="string",
        distinct_count=90,
        sample_values=["great story", "average pacing"],
        row_count=100,
    )

    assert profile["semantic_type"] == "high_cardinality_text"
    assert profile["usable_for_grouping"] is False
