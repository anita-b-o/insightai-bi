import { alpha } from "@mui/material/styles";
import { Box, Stack, Typography } from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { tokens } from "@next/theme/tokens";

import type { AIQueryResponse, VisualizationSuggestion } from "../types";

type ChartType = "bar" | "line" | "pie" | "scatter";
type ChartDatum = Record<string, string | number | null>;

interface ChartModel {
  type: ChartType;
  xKey: string;
  yKey: string;
  data: ChartDatum[];
  reason: string | null;
}

interface ChartRenderState {
  status: "supported" | "unsupported" | "no-data";
  model: ChartModel | null;
}

function parseNumericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed.replace(/\s/g, "").replace(/,/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function isDateLikeValue(value: unknown) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value) && !Number.isNaN(Date.parse(value));
}

function formatChartLabel(label: string) {
  return label
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function truncateAxisLabel(value: string | number) {
  const label = String(value);
  return label.length > 16 ? `${label.slice(0, 15)}…` : label;
}

function formatChartValue(value: number) {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
  }).format(value);
}

function resolveCartesianMargin(type: Exclude<ChartType, "pie">) {
  if (type === "scatter") {
    return { top: 18, right: 18, bottom: 42, left: 28 };
  }
  return { top: 18, right: 18, bottom: 46, left: 20 };
}

function resolveChartHeight(model: ChartModel) {
  if (model.type === "pie") {
    return 296;
  }

  if (model.type === "scatter") {
    return 286;
  }

  return model.data.length <= 6 ? 276 : 288;
}

function buildCategoryAxisProps(dataKey: string) {
  return {
    dataKey,
    tick: { fill: alpha(tokens.color.fg.secondary, 0.82), fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: alpha(tokens.color.border.strong, 0.8) },
    minTickGap: 20,
    interval: "preserveStartEnd" as const,
    height: 48,
    tickMargin: 10,
    tickFormatter: truncateAxisLabel,
  };
}

function buildNumericAxisProps(dataKey?: string) {
  return {
    ...(dataKey ? { dataKey } : {}),
    tick: { fill: alpha(tokens.color.fg.secondary, 0.82), fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: alpha(tokens.color.border.strong, 0.8) },
    width: 56,
  };
}

function shouldPreferTable(model: ChartModel) {
  const labelLengths = model.data.map((item) => String(item[model.xKey] ?? "").trim().length);
  const maxLabelLength = Math.max(...labelLengths, 0);

  if (model.type === "pie") {
    return model.data.length > 6 || maxLabelLength > 18;
  }

  if ((model.type === "bar" || model.type === "line") && model.data.length > 8 && maxLabelLength > 14) {
    return true;
  }

  return false;
}

function normalizeSuggestion(
  suggestion: VisualizationSuggestion | null,
): { type: ChartType | "table"; xKey: string | null; yKey: string | null; reason: string | null } | null {
  if (!suggestion) {
    return null;
  }

  if (suggestion.type === "table_only") {
    return { type: "table", xKey: null, yKey: null, reason: suggestion.reason ?? null };
  }

  if (suggestion.type === "pie") {
    return {
      type: "pie",
      xKey: suggestion.label ?? suggestion.x ?? null,
      yKey: suggestion.value ?? suggestion.y ?? null,
      reason: suggestion.reason ?? null,
    };
  }

  return {
    type: suggestion.type,
    xKey: suggestion.x ?? null,
    yKey: suggestion.y ?? null,
    reason: suggestion.reason ?? null,
  };
}

function getDistinctCount(rows: Record<string, unknown>[], column: string) {
  return new Set(
    rows
      .map((row) => row[column])
      .filter((value) => value !== null && value !== undefined)
      .map((value) => String(value).trim())
      .filter(Boolean),
  ).size;
}

function resolveChartModel(result: AIQueryResponse): ChartModel | null {
  const rows = result.rows;
  const columns = result.columns;

  if (!rows.length || !columns.length) {
    return null;
  }

  const normalizedSuggestion = normalizeSuggestion(result.visualization_suggestion);
  const numericColumns = columns.filter((column) => rows.some((row) => parseNumericValue(row[column]) !== null));

  const buildData = (type: ChartType, xKey: string, yKey: string): ChartDatum[] => {
    return rows
      .slice(0, 50)
      .map((row) => {
        const yValue = parseNumericValue(row[yKey]);
        if (yValue === null) {
          return null;
        }

        const xValue = row[xKey];

        if (type === "scatter") {
          const numericX = parseNumericValue(xValue);
          if (numericX === null) {
            return null;
          }
          return { [xKey]: numericX, [yKey]: yValue };
        }

        if (typeof xValue !== "string" && typeof xValue !== "number") {
          return null;
        }

        return {
          [xKey]: typeof xValue === "number" ? xValue : String(xValue),
          [yKey]: yValue,
        };
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);
  };

  const finalizeModel = (type: ChartType, xKey: string, yKey: string, reason: string | null): ChartModel | null => {
    const data = buildData(type, xKey, yKey);
    if (!data.length) {
      return null;
    }

    if (type === "pie") {
      const distinctCount = new Set(data.map((item) => String(item[xKey] ?? "").trim()).filter(Boolean)).size;
      const positive = data.every((item) => typeof item[yKey] === "number" && (item[yKey] as number) > 0);
      if (distinctCount < 2 || !positive) {
        return null;
      }
    }

    return { type, xKey, yKey, data, reason };
  };

  if (normalizedSuggestion?.type && normalizedSuggestion.type !== "table" && normalizedSuggestion.xKey && normalizedSuggestion.yKey) {
    return finalizeModel(normalizedSuggestion.type, normalizedSuggestion.xKey, normalizedSuggestion.yKey, normalizedSuggestion.reason);
  }

  const primaryNumeric = numericColumns[0];
  if (!primaryNumeric) {
    return null;
  }

  const temporalColumn = columns.find(
    (column) =>
      column !== primaryNumeric &&
      rows.some((row) => row[column] !== null && row[column] !== undefined) &&
      rows.every((row) => row[column] == null || isDateLikeValue(row[column])),
  );
  if (temporalColumn) {
    return finalizeModel("line", temporalColumn, primaryNumeric, "Detected a temporal dimension and numeric metric.");
  }

  const otherNumeric = numericColumns.find((column) => column !== primaryNumeric);
  if (otherNumeric) {
    return finalizeModel("scatter", otherNumeric, primaryNumeric, "Detected two numeric metrics in the result.");
  }

  const categoricalColumn = columns.find(
    (column) => column !== primaryNumeric && rows.some((row) => row[column] !== null && row[column] !== undefined),
  );
  if (!categoricalColumn) {
    return null;
  }

  const distinctCount = getDistinctCount(rows, categoricalColumn);
  if (distinctCount > 0 && distinctCount <= 8) {
    return finalizeModel("pie", categoricalColumn, primaryNumeric, "Detected a low-cardinality category and numeric metric.");
  }

  return finalizeModel("bar", categoricalColumn, primaryNumeric, "Detected a categorical dimension and numeric metric.");
}

export function getChartRenderState(result: AIQueryResponse): ChartRenderState {
  if (!result.rows.length || !result.columns.length) {
    return { status: "no-data", model: null };
  }

  const model = resolveChartModel(result);
  if (!model) {
    return { status: "unsupported", model: null };
  }

  if (shouldPreferTable(model)) {
    return { status: "unsupported", model: null };
  }

  return { status: "supported", model };
}

function TooltipContent({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ color?: string; name?: string | number; value?: string | number | null }>;
  label?: string | number;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <Box
      sx={{
        minWidth: 168,
        px: 1.1,
        py: 0.95,
        borderRadius: tokens.radius.sm,
        border: `1px solid ${alpha(tokens.color.border.subtle, 0.82)}`,
        backgroundColor: tokens.color.bg.surface,
        boxShadow: tokens.shadow.sm,
      }}
    >
      {label ? (
        <Typography variant="caption" sx={{ display: "block", mb: 0.7, color: tokens.color.fg.secondary, fontWeight: 700 }}>
          {typeof label === "string" ? label : String(label)}
        </Typography>
      ) : null}
      <Stack spacing={0.6}>
        {payload.map((item, index) => (
          <Stack key={`${item.name ?? "series"}-${index}`} direction="row" justifyContent="space-between" spacing={1}>
            <Typography variant="caption" sx={{ color: tokens.color.fg.primary }}>
              {formatChartLabel(String(item.name ?? "Value"))}
            </Typography>
            <Typography variant="caption" sx={{ color: tokens.color.fg.primary, fontWeight: 700 }}>
              {typeof item.value === "number" ? formatChartValue(item.value) : String(item.value ?? "-")}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}

function buildChartElement(model: ChartModel, palette: readonly string[]) {
  switch (model.type) {
    case "bar":
      return (
        <BarChart data={model.data} margin={resolveCartesianMargin("bar")}>
          <CartesianGrid stroke={alpha(tokens.color.border.subtle, 0.6)} vertical={false} />
          <XAxis {...buildCategoryAxisProps(model.xKey)} />
          <YAxis {...buildNumericAxisProps()} />
          <Tooltip content={<TooltipContent />} />
          <Legend wrapperStyle={{ paddingTop: 12, fontSize: 11 }} />
          <Bar dataKey={model.yKey} radius={[2, 2, 0, 0]} fill={palette[0]} />
        </BarChart>
      );
    case "line":
      return (
        <LineChart data={model.data} margin={resolveCartesianMargin("line")}>
          <CartesianGrid stroke={alpha(tokens.color.border.subtle, 0.6)} vertical={false} />
          <XAxis {...buildCategoryAxisProps(model.xKey)} />
          <YAxis {...buildNumericAxisProps()} />
          <Tooltip content={<TooltipContent />} />
          <Legend wrapperStyle={{ paddingTop: 12, fontSize: 11 }} />
          <Line type="monotone" dataKey={model.yKey} stroke={palette[1]} strokeWidth={2.5} dot={{ r: 2.5 }} activeDot={{ r: 4 }} />
        </LineChart>
      );
    case "pie":
      return (
        <PieChart margin={{ top: 14, right: 12, bottom: 18, left: 12 }}>
          <Tooltip content={<TooltipContent />} />
          <Legend wrapperStyle={{ paddingTop: 10, fontSize: 11 }} />
          <Pie data={model.data} dataKey={model.yKey} nameKey={model.xKey} innerRadius={40} outerRadius={76} paddingAngle={2}>
            {model.data.map((entry, index) => (
              <Cell key={`${entry[model.xKey] ?? index}`} fill={palette[index % palette.length]} />
            ))}
          </Pie>
        </PieChart>
      );
    case "scatter":
      return (
        <ScatterChart data={model.data} margin={resolveCartesianMargin("scatter")}>
          <CartesianGrid stroke={alpha(tokens.color.border.subtle, 0.6)} />
          <XAxis type="number" {...buildNumericAxisProps(model.xKey)} />
          <YAxis type="number" {...buildNumericAxisProps(model.yKey)} />
          <ZAxis range={[50, 50]} />
          <Tooltip content={<TooltipContent />} cursor={{ strokeDasharray: "3 3" }} />
          <Legend wrapperStyle={{ paddingTop: 12, fontSize: 11 }} />
          <Scatter name={formatChartLabel(model.yKey)} fill={palette[4]} />
        </ScatterChart>
      );
  }
}

export function AIResultChart({ result }: { result: AIQueryResponse }) {
  const chartState = getChartRenderState(result);

  if (chartState.status !== "supported" || !chartState.model) {
    return <EmptyChartState />;
  }

  const model = chartState.model;
  const palette = tokens.color.chart;

  return (
    <Stack
      spacing={0.9}
      sx={{
        width: "100%",
        minWidth: 0,
        py: 0.25,
      }}
    >
      <Typography variant="h6">Suggested visualization</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        {formatChartLabel(model.xKey)} vs {formatChartLabel(model.yKey)}
      </Typography>
      {model.reason ? (
        <Typography variant="caption" color="text.secondary">
          {model.reason}
        </Typography>
      ) : null}

      <Box
        sx={{
          width: "100%",
          height: resolveChartHeight(model),
          minHeight: resolveChartHeight(model),
          minWidth: 0,
          backgroundColor: "transparent",
          borderRadius: 0,
          overflow: "visible",
          pt: 0.45,
          pb: 1.1,
          border: "none",
          boxShadow: "none",
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          {buildChartElement(model, palette)}
        </ResponsiveContainer>
      </Box>
    </Stack>
  );
}

export function EmptyChartState({
  title = "Table-first view",
  description = "The result is clearer as a table for this shape or label density.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <Stack
      spacing={0.9}
      sx={{
        width: "100%",
        minWidth: 0,
        py: 0.25,
      }}
    >
      <Typography variant="h6">Suggested visualization</Typography>
      <Box
        sx={{
          width: "100%",
          minHeight: 132,
          borderRadius: 0,
          border: "none",
          backgroundColor: "transparent",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          p: 0,
          textAlign: "left",
        }}
      >
        <Stack
          spacing={0.45}
          sx={{
            maxWidth: 320,
            pl: 1.25,
            borderLeft: `2px solid ${alpha(tokens.color.border.strong, 0.48)}`,
          }}
        >
          <Typography variant="body1" sx={{ color: tokens.color.fg.primary, fontWeight: 700 }}>
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        </Stack>
      </Box>
    </Stack>
  );
}
