from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AIQueryRequest(BaseModel):
    dataset_id: int = Field(gt=0)
    question: str = Field(min_length=3, max_length=4000)


class AIInsightsRequest(BaseModel):
    dataset_id: int = Field(gt=0)


class AIInsightRefreshRequest(BaseModel):
    dataset_id: int = Field(gt=0)


class AIQueryMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_id: int
    dataset_name: str
    column_count: int
    model: str
    fallback_used: bool = False
    cache_hit: bool = False


class AIVisualizationSuggestion(BaseModel):
    type: str
    x: str | None = None
    y: str | None = None
    label: str | None = None
    value: str | None = None
    reason: str | None = None


class SQLAnalysisResult(BaseModel):
    is_aggregated: bool = False
    aggregation_functions: list[str] = Field(default_factory=list)
    group_by_columns: list[str] = Field(default_factory=list)
    selected_columns: list[str] = Field(default_factory=list)
    has_group_by: bool = False
    has_order_by: bool = False
    has_limit: bool = False


class AIQueryResponse(BaseModel):
    query_id: int | None = None
    answer: str
    sql: str | None = None
    rows: list[dict[str, object]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    chart_suggestion: str | None = None
    visualization_suggestion: AIVisualizationSuggestion | None = None
    sql_analysis: SQLAnalysisResult | None = None
    metadata: AIQueryMetadata | None = None


class AIInsightRankingMetadata(BaseModel):
    global_score: float | None = Field(default=None, ge=0, le=1)
    quality_component: float | None = Field(default=None, ge=0, le=1)
    feature_importance_component: float | None = Field(default=None, ge=0, le=1)
    impact_component: float | None = Field(default=None, ge=0, le=1)
    confidence_component: float | None = Field(default=None, ge=0, le=1)
    diversity_penalty: float | None = Field(default=None, ge=0)
    deduplication_key: str | None = None
    selected_reason: str | None = None


class AIInsight(BaseModel):
    type: str
    id: str
    title: str
    description: str
    summary: str
    severity: Literal["info", "warning", "critical"] = "info"
    metric: str | None = None
    dimension: str | None = None
    value: int | float | str | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)
    impact: float = Field(ge=0, le=1, default=0.5)
    quality_score: int = Field(ge=0, le=100, default=50)
    priority: Literal["high", "medium", "low"] = "medium"
    sql: str | None = None
    chart_suggestion: Literal["bar", "line", "pie", "scatter", "table"] | None = None
    chart_type: Literal["bar", "line", "pie", "scatter", "table"] = "table"
    data: list[dict[str, object]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, object]] = Field(default_factory=list)
    visualization_suggestion: AIVisualizationSuggestion | None = None
    ranking_metadata: AIInsightRankingMetadata | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        summary = payload.get("summary")
        description = payload.get("description")
        if not isinstance(summary, str) or not summary.strip():
            if isinstance(description, str) and description.strip():
                payload["summary"] = description.strip()
        if not isinstance(description, str) or not description.strip():
            if isinstance(payload.get("summary"), str) and payload["summary"].strip():
                payload["description"] = payload["summary"].strip()

        if payload.get("chart_suggestion") is None and isinstance(payload.get("visualization_suggestion"), dict):
            suggestion_type = payload["visualization_suggestion"].get("type")
            if suggestion_type == "table_only":
                payload["chart_suggestion"] = "table"
            elif suggestion_type in {"bar", "line", "pie"}:
                payload["chart_suggestion"] = suggestion_type

        if payload.get("chart_type") is None:
            chart_type = payload.get("chart_suggestion")
            if chart_type == "table" or chart_type is None:
                payload["chart_type"] = "table"
            elif chart_type in {"bar", "line", "pie", "scatter"}:
                payload["chart_type"] = chart_type

        if payload.get("data") is None and isinstance(payload.get("rows"), list):
            payload["data"] = payload["rows"]
        if payload.get("rows") is None and isinstance(payload.get("data"), list):
            payload["rows"] = payload["data"]

        if not payload.get("id"):
            metric = str(payload.get("metric") or "metric").strip().lower().replace(" ", "_")
            dimension = str(payload.get("dimension") or "dimension").strip().lower().replace(" ", "_")
            insight_type = str(payload.get("type") or "insight").strip().lower().replace(" ", "_")
            payload["id"] = f"{insight_type}:{metric}:{dimension}"

        return payload

    @model_validator(mode="after")
    def sync_description(self) -> "AIInsight":
        self.summary = self.summary.strip()
        self.description = self.description.strip() if self.description.strip() else self.summary
        self.summary = self.description
        if not self.data:
            self.data = self.rows
        if not self.rows:
            self.rows = self.data
        self.chart_type = self.chart_type or "table"
        return self


class AIInsightNarrative(BaseModel):
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    risks_or_caveats: list[str] = Field(default_factory=list)
    recommended_next_questions: list[str] = Field(default_factory=list)


class AIInsightsResponse(BaseModel):
    run_id: int | None = None
    dataset_id: int
    dataset_name: str
    status: Literal["success", "failed"] = "success"
    generated_at: str
    is_stale: bool = False
    error_message: str | None = None
    insights: list[AIInsight] = Field(default_factory=list)
    narrative: AIInsightNarrative = Field(default_factory=AIInsightNarrative)


class DatasetInsightRunSummary(BaseModel):
    id: int
    dataset_id: int
    dataset_name: str
    status: Literal["success", "failed"]
    generated_at: str
    created_at: str
    updated_at: str
    is_stale: bool = False
    error_message: str | None = None


class DatasetInsightRunDetail(DatasetInsightRunSummary):
    insights: list[AIInsight] = Field(default_factory=list)


class AIQueryHistorySummary(BaseModel):
    id: int
    dataset_id: int
    question: str
    title: str | None = None
    is_favorite: bool = False
    generated_sql: str | None = None
    execution_time_ms: int | None = None
    created_at: str
    updated_at: str


class AIQueryHistoryDetail(BaseModel):
    id: int
    dataset_id: int
    question: str
    title: str | None = None
    is_favorite: bool = False
    generated_sql: str | None = None
    execution_time_ms: int | None = None
    created_at: str
    updated_at: str
    result: AIQueryResponse | None = None


class AIQueryHistoryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    is_favorite: bool | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None
