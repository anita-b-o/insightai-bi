import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

import { Box, Stack, useMediaQuery, useTheme } from "@mui/material";
import { type ReactNode } from "react";
import { Responsive, type Layout, type LayoutItem, type ResponsiveLayouts, useContainerWidth } from "react-grid-layout";

import type { DashboardWidget as DashboardWidgetModel } from "../types";

const BREAKPOINT_COLS = {
  lg: 12,
  md: 10,
  sm: 6,
  xs: 1,
  xxs: 1,
} as const;

function resolveMinimumHeight(widget: DashboardWidgetModel) {
  if (widget.widget_type === "chart" || widget.type === "chart") {
    return 13;
  }

  if (widget.widget_type === "insight" || widget.type === "insight") {
    return 13;
  }

  return 9;
}

function buildGridLayouts(widgets: DashboardWidgetModel[]): ResponsiveLayouts {
  const mapWidget = (widget: DashboardWidgetModel, cols: number): LayoutItem => {
    const width = cols <= 1 ? 1 : Math.min(widget.layout.width, cols);
    const x = cols <= 1 ? 0 : Math.min(widget.layout.x, Math.max(0, cols - width));
    const minHeight = resolveMinimumHeight(widget);

    return {
      i: String(widget.id),
      x,
      y: widget.layout.y,
      w: width,
      h: Math.max(widget.layout.height, minHeight),
      minW: cols <= 1 ? 1 : Math.min(3, cols),
      minH: minHeight,
      static: true,
    };
  };

  const buildForCols = (cols: number): Layout => {
    const orderedWidgets = [...widgets].sort((left, right) => left.layout.order - right.layout.order);
    const columnHeights = Array.from({ length: cols }, () => 0);

    return orderedWidgets.map((widget) => {
      const item = mapWidget(widget, cols);
      const firstColumn = Math.max(0, Math.min(item.x, cols - item.w));
      const occupiedColumns = Array.from({ length: item.w }, (_, index) => firstColumn + index).filter((column) => column < cols);
      const nextY = Math.max(item.y, ...occupiedColumns.map((column) => columnHeights[column] ?? 0));

      item.x = firstColumn;
      item.y = nextY;
      occupiedColumns.forEach((column) => {
        columnHeights[column] = nextY + item.h;
      });

      return item;
    });
  };

  return {
    lg: buildForCols(BREAKPOINT_COLS.lg),
    md: buildForCols(BREAKPOINT_COLS.md),
    sm: buildForCols(BREAKPOINT_COLS.sm),
    xs: buildForCols(BREAKPOINT_COLS.xs),
    xxs: buildForCols(BREAKPOINT_COLS.xxs),
  };
}

export function DashboardGrid({
  widgets,
  renderWidget,
}: {
  widgets: DashboardWidgetModel[];
  renderWidget: (widget: DashboardWidgetModel) => ReactNode;
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const { width, mounted, containerRef } = useContainerWidth({ initialWidth: 1280 });
  const useStackFallback = isMobile || !mounted || width < 320;

  if (useStackFallback) {
    return (
      <Stack ref={containerRef} spacing={2} sx={{ width: "100%" }}>
        {widgets.map((widget) => (
          <Box key={widget.id}>{renderWidget(widget)}</Box>
        ))}
      </Stack>
    );
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        width: "100%",
        minWidth: 0,
        "& .dashboard-grid-layout": {
          minHeight: 120,
          width: "100% !important",
        },
        "& .react-grid-item": {
          background: "transparent",
          transition: "transform 160ms ease",
        },
        "& .react-grid-item > *": {
          width: "100%",
          height: "100%",
          minHeight: 0,
        },
      }}
    >
      {mounted ? (
        <Responsive
          width={width}
          className="dashboard-grid-layout"
          layouts={buildGridLayouts(widgets)}
          breakpoints={{ lg: 1200, md: 900, sm: 600, xs: 360, xxs: 0 }}
          cols={BREAKPOINT_COLS}
          rowHeight={36}
          margin={[20, 20]}
          containerPadding={[0, 0]}
          dragConfig={{ enabled: false }}
          resizeConfig={{ enabled: false }}
        >
          {widgets.map((widget) => (
            <Box key={String(widget.id)}>{renderWidget(widget)}</Box>
          ))}
        </Responsive>
      ) : null}
    </Box>
  );
}
