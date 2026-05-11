import type { AIQueryResponse, VisualizationSuggestion } from "@next/features/ai/types";

export type ResultRow = Record<string, string | number | boolean | null>;
export type ChartType = "bar" | "line" | "pie" | "scatter" | "table";

export interface ChartDatum {
  [key: string]: string | number | null;
}

export interface ResolvedChartModel {
  type: Exclude<ChartType, "table">;
  xKey: string;
  yKey: string;
  data: ChartDatum[];
  reason: string | null;
}

const MAX_CHART_ROWS = 50;

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function parseNumericValue(value: unknown): number | null {
  if (isFiniteNumber(value)) {
    return value;
  }

  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const normalized = trimmed.replace(/\s/g, "").replace(/,/g, "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isDateLikeValue(value: unknown): boolean {
  if (typeof value !== "string") {
    return false;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }

  if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
    return !Number.isNaN(Date.parse(trimmed));
  }

  return false;
}

function normalizeChartType(type: string | null | undefined): ChartType | null {
  if (!type) {
    return null;
  }
  if (type === "table_only") {
    return "table";
  }
  if (type === "bar" || type === "line" || type === "pie" || type === "scatter" || type === "table") {
    return type;
  }
  return null;
}

function getDistinctCount(rows: Record<string, unknown>[], column: string): number {
  return new Set(
    rows
      .map((row) => row[column])
      .filter((value) => value !== null && value !== undefined)
      .map((value) => String(value).trim())
      .filter(Boolean),
  ).size;
}

function pickNumericColumns(rows: Record<string, unknown>[], columns: string[]): string[] {
  return columns.filter((column) =>
    rows.some((row) => parseNumericValue(row[column]) !== null),
  );
}

function pickTemporalColumn(rows: Record<string, unknown>[], columns: string[]): string | null {
  for (const column of columns) {
    const values = rows.map((row) => row[column]).filter((value) => value !== null && value !== undefined);
    if (values.length > 0 && values.every((value) => isDateLikeValue(value))) {
      return column;
    }
  }
  return null;
}

function pickCategoricalColumn(rows: Record<string, unknown>[], columns: string[], excluded: string[]): string | null {
  const candidates = columns.filter((column) => !excluded.includes(column));
  for (const column of candidates) {
    const values = rows.map((row) => row[column]).filter((value) => value !== null && value !== undefined);
    if (values.length > 0) {
      return column;
    }
  }
  return null;
}

function resolveColumnByHint(columns: string[], hint: string | null | undefined): string | null {
  if (!hint) {
    return null;
  }

  const normalizedHint = hint.trim().toLowerCase();
  if (!normalizedHint) {
    return null;
  }

  const exactMatch = columns.find((column) => column.toLowerCase() === normalizedHint);
  if (exactMatch) {
    return exactMatch;
  }

  const aliasMap: Record<string, string[]> = {
    metric: ["metric", "value", "total", "amount", "count", "correlation", "y"],
    dimension: ["dimension", "category", "label", "group", "period", "x"],
  };

  for (const column of columns) {
    const normalizedColumn = column.toLowerCase();
    if (normalizedColumn.includes(normalizedHint) || normalizedHint.includes(normalizedColumn)) {
      return column;
    }
    const aliases = aliasMap[normalizedHint];
    if (aliases?.includes(normalizedColumn)) {
      return column;
    }
  }

  return null;
}

function normalizeBackendSuggestion(
  suggestion: VisualizationSuggestion | null,
): { type: ChartType; xKey: string | null; yKey: string | null; reason: string | null } | null {
  if (!suggestion) {
    return null;
  }

  const normalizedType = normalizeChartType(suggestion.type);
  if (!normalizedType) {
    return null;
  }

  if (normalizedType === "table") {
    return { type: "table", xKey: null, yKey: null, reason: suggestion.reason ?? null };
  }

  if (normalizedType === "pie") {
    return {
      type: "pie",
      xKey: suggestion.label ?? suggestion.x ?? null,
      yKey: suggestion.value ?? suggestion.y ?? null,
      reason: suggestion.reason ?? null,
    };
  }

  return {
    type: normalizedType,
    xKey: suggestion.x ?? null,
    yKey: suggestion.y ?? null,
    reason: suggestion.reason ?? null,
  };
}

function inferChartType(
  rows: Record<string, unknown>[],
  columns: string[],
): { type: ChartType; xKey: string | null; yKey: string | null; reason: string | null } {
  const numericColumns = pickNumericColumns(rows, columns);
  const primaryNumeric = numericColumns[0] ?? null;
  if (!primaryNumeric) {
    return { type: "table", xKey: null, yKey: null, reason: null };
  }

  const temporalColumn = pickTemporalColumn(rows, columns.filter((column) => column !== primaryNumeric));
  if (temporalColumn) {
    return {
      type: "line",
      xKey: temporalColumn,
      yKey: primaryNumeric,
      reason: "Detected a temporal column and numeric metric in the result.",
    };
  }

  const categoricalColumn = pickCategoricalColumn(rows, columns, [primaryNumeric]);
  if (!categoricalColumn) {
    return { type: "table", xKey: null, yKey: null, reason: null };
  }

  const distinctCount = getDistinctCount(rows, categoricalColumn);
  if (distinctCount > 0 && distinctCount <= 8) {
    return {
      type: "pie",
      xKey: categoricalColumn,
      yKey: primaryNumeric,
      reason: "Detected a low-cardinality category and numeric metric in the result.",
    };
  }

  return {
    type: "bar",
    xKey: categoricalColumn,
    yKey: primaryNumeric,
    reason: "Detected a categorical column and numeric metric in the result.",
  };
}

function buildCategoricalSeriesData(
  rows: Record<string, unknown>[],
  xKey: string,
  yKey: string,
  options: { sortByX: boolean },
): ChartDatum[] {
  const data: ChartDatum[] = rows
    .slice(0, MAX_CHART_ROWS)
    .map((row) => {
      const xValue = row[xKey];
      const yValue = parseNumericValue(row[yKey]);

      if ((typeof xValue !== "string" && typeof xValue !== "number") || yValue === null) {
        return null;
      }

      return {
        [xKey]: typeof xValue === "number" ? xValue : String(xValue),
        [yKey]: yValue,
      };
    })
    .filter((item) => item !== null);

  if (options.sortByX) {
    data.sort((left, right) => {
      const leftValue = left[xKey];
      const rightValue = right[xKey];
      const leftTime = typeof leftValue === "string" ? Date.parse(leftValue) : Number(leftValue);
      const rightTime = typeof rightValue === "string" ? Date.parse(rightValue) : Number(rightValue);
      return leftTime - rightTime;
    });
  }

  return data;
}

function buildScatterData(rows: Record<string, unknown>[], xKey: string, yKey: string): ChartDatum[] {
  const data: ChartDatum[] = rows
    .slice(0, MAX_CHART_ROWS)
    .map((row) => {
      const xValue = parseNumericValue(row[xKey]);
      const yValue = parseNumericValue(row[yKey]);
      if (xValue === null || yValue === null) {
        return null;
      }
      return {
        [xKey]: xValue,
        [yKey]: yValue,
      };
    })
    .filter((item) => item !== null);

  return data;
}

function getDistinctLabelCount(data: ChartDatum[], labelKey: string): number {
  return new Set(
    data
      .map((datum) => datum[labelKey])
      .filter((value) => typeof value === "string" || typeof value === "number")
      .map((value) => String(value).trim())
      .filter(Boolean),
  ).size;
}

function isValidPieData(data: ChartDatum[], xKey: string, yKey: string): boolean {
  if (data.length < 2) {
    return false;
  }

  if (getDistinctLabelCount(data, xKey) < 2) {
    return false;
  }

  let total = 0;
  for (const datum of data) {
    const value = datum[yKey];
    if (!isFiniteNumber(value) || value <= 0) {
      return false;
    }
    total += value;
  }

  return total > 0;
}

function isValidBarOrLineData(data: ChartDatum[], xKey: string, yKey: string): boolean {
  if (data.length < 1) {
    return false;
  }

  const hasValidNumericValue = data.some((datum) => isFiniteNumber(datum[yKey]));
  if (!hasValidNumericValue) {
    return false;
  }

  // Prefer distinct labels; if there are none the chart is technically renderable but low-signal.
  return data.some((datum) => datum[xKey] !== null && datum[xKey] !== undefined);
}

function isValidScatterData(data: ChartDatum[], xKey: string, yKey: string): boolean {
  if (data.length < 5) {
    return false;
  }

  const distinctX = new Set<number>();
  const distinctY = new Set<number>();

  for (const datum of data) {
    const xValue = datum[xKey];
    const yValue = datum[yKey];
    if (!isFiniteNumber(xValue) || !isFiniteNumber(yValue)) {
      return false;
    }
    distinctX.add(xValue);
    distinctY.add(yValue);
  }

  return distinctX.size >= 2 && distinctY.size >= 2;
}

function isChartDataValid(type: Exclude<ChartType, "table">, data: ChartDatum[], xKey: string, yKey: string): boolean {
  if (type === "pie") {
    return isValidPieData(data, xKey, yKey);
  }
  if (type === "scatter") {
    return isValidScatterData(data, xKey, yKey);
  }
  return isValidBarOrLineData(data, xKey, yKey);
}

function resolveForcedKeys(
  result: AIQueryResponse,
  forcedType: Exclude<ChartType, "table">,
): { xKey: string | null; yKey: string | null } {
  const columns = result.columns;
  const rows = result.rows;
  const numericColumns = pickNumericColumns(rows, columns);

  const hintedX = resolveColumnByHint(columns, result.preferred_chart_dimension);
  const hintedY = resolveColumnByHint(columns, result.preferred_chart_metric);

  if (forcedType === "scatter") {
    const xKey = hintedX && numericColumns.includes(hintedX) ? hintedX : numericColumns[0] ?? null;
    const yKey = hintedY && numericColumns.includes(hintedY) ? hintedY : numericColumns.find((column) => column !== xKey) ?? null;
    return { xKey, yKey };
  }

  const backendSuggestion = normalizeBackendSuggestion(result.visualization_suggestion);
  if (backendSuggestion && backendSuggestion.type === forcedType && backendSuggestion.xKey && backendSuggestion.yKey) {
    return { xKey: backendSuggestion.xKey, yKey: backendSuggestion.yKey };
  }

  if (forcedType === "line") {
    const xKey = hintedX ?? pickTemporalColumn(rows, columns.filter((column) => column !== hintedY));
    const yKey = hintedY ?? numericColumns[0] ?? null;
    return { xKey, yKey };
  }

  if (forcedType === "pie") {
    const yKey = hintedY ?? resolveColumnByHint(columns, "metric") ?? numericColumns[0] ?? null;
    const xKey =
      hintedX ??
      resolveColumnByHint(columns, "dimension") ??
      resolveColumnByHint(columns, "category") ??
      pickCategoricalColumn(rows, columns, yKey ? [yKey] : []);
    return { xKey, yKey };
  }

  const yKey = hintedY ?? resolveColumnByHint(columns, "metric") ?? numericColumns[0] ?? null;
  const xKey =
    hintedX ??
    resolveColumnByHint(columns, "dimension") ??
    resolveColumnByHint(columns, "category") ??
    pickCategoricalColumn(rows, columns, yKey ? [yKey] : []);
  return { xKey, yKey };
}

export function resolveChartModel(result: AIQueryResponse): ResolvedChartModel | null {
  if (!result.rows?.length || !result.columns?.length) {
    return null;
  }

  const forcedType = normalizeChartType(result.preferred_chart_type);
  if (forcedType) {
    if (forcedType === "table") {
      return null;
    }

    const { xKey, yKey } = resolveForcedKeys(result, forcedType);
    if (!xKey || !yKey) {
      return null;
    }

    const data =
      forcedType === "scatter"
        ? buildScatterData(result.rows, xKey, yKey)
        : buildCategoricalSeriesData(result.rows, xKey, yKey, {
            sortByX: forcedType === "line" && result.rows.some((row) => isDateLikeValue(row[xKey])),
          });

    if (!isChartDataValid(forcedType, data, xKey, yKey)) {
      return null;
    }

    return {
      type: forcedType,
      xKey,
      yKey,
      data,
      reason: result.visualization_suggestion?.reason ?? null,
    };
  }

  const backendSuggestion = normalizeBackendSuggestion(result.visualization_suggestion);
  const resolved = backendSuggestion ?? inferChartType(result.rows, result.columns);

  if (resolved.type === "table" || !resolved.xKey || !resolved.yKey) {
    return null;
  }

  const data = resolved.type === "scatter"
    ? buildScatterData(result.rows, resolved.xKey, resolved.yKey)
    : buildCategoricalSeriesData(result.rows, resolved.xKey, resolved.yKey, {
        sortByX: resolved.type === "line" && result.rows.some((row) => isDateLikeValue(row[resolved.xKey!])),
      });

  if (!isChartDataValid(resolved.type, data, resolved.xKey, resolved.yKey)) {
    return null;
  }

  return {
    type: resolved.type,
    xKey: resolved.xKey,
    yKey: resolved.yKey,
    data,
    reason: resolved.reason ?? null,
  };
}
