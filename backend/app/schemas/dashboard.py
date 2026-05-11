from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.ai import AIInsight, AIQueryResponse

DashboardWidgetType = Literal["chart", "table", "insight"]
DashboardChartType = Literal["bar", "line", "pie", "scatter", "table"]
DashboardSourceType = Literal["ask_ai", "query", "insight", "manual"]
DashboardExecutionType = Literal["snapshot", "query", "insight"]
DashboardExecutionStatus = Literal["never_run", "success", "failed"]
DashboardFreshnessStatus = Literal["fresh", "stale", "failed", "never_refreshed"]


class DashboardLayout(BaseModel):
    column_span: int = Field(default=1, ge=1, le=2)
    order: int = Field(default=0, ge=0)
    use_snapshot: bool = False
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    width: int = Field(default=6, ge=1, le=24)
    height: int = Field(default=4, ge=1, le=24)


class DashboardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    dataset_id: int | None = Field(default=None, gt=0)
    auto_refresh_enabled: bool = False
    refresh_interval_minutes: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_refresh_settings(self) -> "DashboardCreate":
        if self.auto_refresh_enabled and self.refresh_interval_minutes is None:
            raise ValueError("refresh_interval_minutes is required when auto_refresh_enabled is true")
        if not self.auto_refresh_enabled:
            self.refresh_interval_minutes = None
        return self


class DashboardCreateRequest(DashboardCreate):
    pass


class DashboardUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    dataset_id: int | None = Field(default=None, gt=0)
    auto_refresh_enabled: bool | None = None
    refresh_interval_minutes: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def validate_refresh_settings(self) -> "DashboardUpdateRequest":
        if self.auto_refresh_enabled is True and self.refresh_interval_minutes is None:
            raise ValueError("refresh_interval_minutes is required when auto_refresh_enabled is true")
        if self.auto_refresh_enabled is False:
            self.refresh_interval_minutes = None
        return self


class DashboardWidgetCreate(BaseModel):
    type: DashboardWidgetType | None = None
    widget_type: DashboardWidgetType | None = None
    source_type: DashboardSourceType
    source_id: int | None = Field(default=None, gt=0)
    execution_type: DashboardExecutionType | None = None
    chart_type: DashboardChartType | None = None
    query_sql: str | None = None
    layout: DashboardLayout = Field(default_factory=DashboardLayout)
    title: str | None = Field(default=None, max_length=255)
    config_json: dict[str, Any] | None = None
    data_json: list[dict[str, Any]] | dict[str, Any] | None = None
    insight_index: int | None = Field(default=None, ge=0)
    save_snapshot: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if payload.get("type") is None and payload.get("widget_type") is not None:
            payload["type"] = payload["widget_type"]
        if payload.get("widget_type") is None and payload.get("type") is not None:
            payload["widget_type"] = payload["type"]
        source_type = payload.get("source_type")
        if source_type == "ask_ai":
            payload["source_type"] = "query"
        return payload

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def validate_widget(self) -> "DashboardWidgetCreate":
        widget_type = self.type or self.widget_type
        self.type = widget_type
        self.widget_type = widget_type
        if widget_type is None:
            raise ValueError("widget_type is required")
        if self.source_type == "manual":
            self.save_snapshot = False
        elif self.source_id is None:
            raise ValueError("source_id is required unless source_type is manual")
        if self.execution_type is None:
            if self.source_type == "query":
                self.execution_type = "query"
            elif self.source_type == "insight":
                self.execution_type = "insight"
            else:
                self.execution_type = "snapshot"
        if widget_type != "chart" and self.chart_type is None:
            self.chart_type = "table"
        return self


class DashboardWidgetCreateRequest(DashboardWidgetCreate):
    pass


class DashboardWidgetUpdate(BaseModel):
    type: DashboardWidgetType | None = None
    widget_type: DashboardWidgetType | None = None
    execution_type: DashboardExecutionType | None = None
    chart_type: DashboardChartType | None = None
    query_sql: str | None = None
    layout: DashboardLayout | None = None
    title: str | None = Field(default=None, max_length=255)
    config_json: dict[str, Any] | None = None
    data_json: list[dict[str, Any]] | dict[str, Any] | None = None
    insight_index: int | None = Field(default=None, ge=0)
    save_snapshot: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if payload.get("type") is None and payload.get("widget_type") is not None:
            payload["type"] = payload["widget_type"]
        if payload.get("widget_type") is None and payload.get("type") is not None:
            payload["widget_type"] = payload["type"]
        return payload

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def sync_widget_type(self) -> "DashboardWidgetUpdate":
        widget_type = self.type or self.widget_type
        if widget_type is not None:
            self.type = widget_type
            self.widget_type = widget_type
        return self


class DashboardWidgetUpdateRequest(DashboardWidgetUpdate):
    pass


class DashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dataset_id: int | None = None
    auto_refresh_enabled: bool = False
    refresh_interval_minutes: int | None = None
    last_successful_refresh_at: str | None = None
    next_refresh_at: str | None = None
    freshness_status: DashboardFreshnessStatus = "never_refreshed"
    created_at: str
    updated_at: str
    widget_count: int


class DashboardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dataset_id: int | None = None
    auto_refresh_enabled: bool = False
    refresh_interval_minutes: int | None = None
    last_successful_refresh_at: str | None = None
    next_refresh_at: str | None = None
    freshness_status: DashboardFreshnessStatus = "never_refreshed"
    created_at: str
    updated_at: str
    widgets: list["DashboardWidgetRead"] = Field(default_factory=list)


class DashboardRefreshSettingsRequest(BaseModel):
    auto_refresh_enabled: bool
    refresh_interval_minutes: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_settings(self) -> "DashboardRefreshSettingsRequest":
        if self.auto_refresh_enabled and self.refresh_interval_minutes is None:
            raise ValueError("refresh_interval_minutes is required when auto_refresh_enabled is true")
        if not self.auto_refresh_enabled:
            self.refresh_interval_minutes = None
        return self


class DashboardWidgetReorderItem(BaseModel):
    widget_id: int = Field(gt=0)
    order: int = Field(ge=0)


class DashboardSnapshotModeRequest(BaseModel):
    use_snapshot: bool


class DashboardSnapshotRefreshFailure(BaseModel):
    widget_id: int
    reason: str


class DashboardWidgetResolvedSource(BaseModel):
    query: AIQueryResponse | None = None
    insight: AIInsight | None = None


class DashboardWidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    type: DashboardWidgetType
    widget_type: DashboardWidgetType
    source_type: DashboardSourceType
    source_id: int | None = None
    execution_type: DashboardExecutionType = "snapshot"
    execution_status: DashboardExecutionStatus = "never_run"
    chart_type: DashboardChartType | None = None
    query_sql: str | None = None
    layout: DashboardLayout
    title: str | None = None
    config_json: dict[str, Any] | None = None
    data_json: list[dict[str, Any]] | dict[str, Any] | None = None
    last_run_at: str | None = None
    error_message: str | None = None
    insight_index: int | None = None
    has_snapshot: bool = False
    using_snapshot: bool = False
    snapshot_created_at: str | None = None
    source_changed: bool = False
    created_at: str
    source: DashboardWidgetResolvedSource


class DashboardDetail(DashboardRead):
    widgets: list[DashboardWidgetRead]


class DashboardNarrative(BaseModel):
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    risks_or_caveats: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    stale_or_failed_widgets: list[str] = Field(default_factory=list)


class DashboardShareLinkCreateRequest(BaseModel):
    expires_at: str | None = None


class DashboardShareLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    expires_at: str | None = None
    revoked_at: str | None = None
    created_at: str
    share_url: str


class DashboardShareLinkCreateResponse(DashboardShareLinkRead):
    token: str


class SharedDashboardWidgetRead(BaseModel):
    id: int
    dashboard_id: int
    type: DashboardWidgetType
    widget_type: DashboardWidgetType
    source_type: DashboardSourceType
    execution_type: DashboardExecutionType = "snapshot"
    execution_status: DashboardExecutionStatus = "never_run"
    chart_type: DashboardChartType | None = None
    layout: DashboardLayout
    title: str | None = None
    config_json: dict[str, Any] | None = None
    data_json: list[dict[str, Any]] | dict[str, Any] | None = None
    last_run_at: str | None = None
    error_message: str | None = None
    created_at: str


class SharedDashboardRead(BaseModel):
    id: int
    name: str
    freshness_status: DashboardFreshnessStatus = "never_refreshed"
    last_successful_refresh_at: str | None = None
    next_refresh_at: str | None = None
    narrative: DashboardNarrative = Field(default_factory=DashboardNarrative)
    widgets: list[SharedDashboardWidgetRead] = Field(default_factory=list)


class DashboardBulkSnapshotRefreshResponse(BaseModel):
    refreshed_count: int
    failed_count: int
    failures: list[DashboardSnapshotRefreshFailure] = Field(default_factory=list)
    dashboard: DashboardDetail
