from types import SimpleNamespace

from app.services import dashboard_narrative_service


def _dashboard(name: str = "Executive overview"):
    return SimpleNamespace(id=3, name=name)


def _widget(
    *,
    widget_id: int = 1,
    title: str = "Revenue by month",
    execution_status: str = "success",
    chart_type: str = "bar",
    source_type: str = "query",
    data_json=None,
    query_sql: str | None = "select * from dataset",
    error_message: str | None = None,
    source_changed: bool = False,
):
    return SimpleNamespace(
        id=widget_id,
        title=title,
        execution_status=execution_status,
        chart_type=chart_type,
        source_type=source_type,
        data_json=data_json if data_json is not None else [{"month": "2026-04", "revenue": 120}],
        execution_type="query" if source_type == "query" else "insight" if source_type == "insight" else "snapshot",
        query_sql=query_sql,
        error_message=error_message,
        source_changed=source_changed,
    )


def test_narrative_with_successful_widgets():
    narrative = dashboard_narrative_service.generate_dashboard_narrative(
        _dashboard(),
        [
            _widget(title="Revenue by month"),
            _widget(widget_id=2, title="Top channels", source_type="insight", chart_type="pie"),
        ],
    )

    assert narrative.summary
    assert narrative.key_findings
    assert any("Revenue by month" in item for item in narrative.key_findings)


def test_narrative_with_failed_widgets():
    narrative = dashboard_narrative_service.generate_dashboard_narrative(
        _dashboard(),
        [
            _widget(execution_status="failed", error_message="Broken SQL"),
        ],
    )

    assert any("failed" in item.lower() for item in narrative.risks_or_caveats)
    assert any("Broken SQL" in item for item in narrative.stale_or_failed_widgets)


def test_narrative_with_empty_widgets():
    narrative = dashboard_narrative_service.generate_dashboard_narrative(
        _dashboard(),
        [
            _widget(data_json=[]),
        ],
    )

    assert any("empty" in item.lower() or "no usable data" in item.lower() for item in narrative.risks_or_caveats)
    assert narrative.stale_or_failed_widgets


def test_recommended_actions_are_not_empty():
    narrative = dashboard_narrative_service.generate_dashboard_narrative(
        _dashboard(),
        [
            _widget(execution_status="never_run", query_sql=None, data_json=[]),
        ],
    )

    assert narrative.recommended_next_actions
