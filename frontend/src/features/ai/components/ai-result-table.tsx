import { alpha } from "@mui/material/styles";
import { Box, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import { DataTableFrame } from "@next/components/ui/data-table";
import { tokens } from "@next/theme/tokens";

import { formatResultCellValue, formatResultColumnLabel } from "../types";

interface AIResultTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
  maxHeight?: number | string;
  maxRows?: number;
  compact?: boolean;
  title?: string;
}

export function AIResultTable({
  columns,
  rows,
  maxHeight,
  maxRows,
  compact = false,
  title = "Query results",
}: AIResultTableProps) {
  if (!columns.length || !rows.length) {
    return null;
  }

  const visibleRows = typeof maxRows === "number" ? rows.slice(0, maxRows) : rows;

  return (
    <Box sx={{ width: "100%", minWidth: 0 }}>
      <Typography variant="h6" sx={{ mb: compact ? 1 : 1.25 }}>
        {title}
      </Typography>
      <DataTableFrame maxHeight={maxHeight}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column}
                  sx={{
                    backgroundColor: alpha(tokens.color.bg.surface, 0.98),
                    borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.8)}`,
                    color: alpha(tokens.color.fg.secondary, 0.92),
                    fontWeight: 700,
                    fontSize: 13,
                    letterSpacing: "0.03em",
                    whiteSpace: "nowrap",
                    py: compact ? 1 : 1.2,
                    px: compact ? 1.4 : 1.75,
                    minWidth: 140,
                  }}
                >
                  {formatResultColumnLabel(column)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleRows.map((row, rowIndex) => (
              <TableRow
                key={`result-row-${rowIndex}`}
                hover
                sx={{
                  backgroundColor: rowIndex % 2 === 0 ? tokens.color.bg.surface : alpha(tokens.color.bg.surfaceMuted, 0.5),
                  "&:hover": {
                    backgroundColor: alpha(tokens.color.bg.surfaceMuted, 0.8),
                  },
                }}
              >
                {columns.map((column) => {
                  const value = row[column];
                  return (
                    <TableCell
                      key={`${rowIndex}-${column}`}
                      sx={{
                        borderBottom: `1px solid ${alpha(tokens.color.border.subtle, 0.74)}`,
                        py: compact ? 0.95 : 1.1,
                        lineHeight: 1.5,
                        px: compact ? 1.4 : 1.75,
                        fontSize: 13,
                        textAlign: typeof value === "number" ? "right" : "left",
                        color: typeof value === "number" ? tokens.color.fg.primary : alpha(tokens.color.fg.primary, 0.92),
                        fontWeight: typeof value === "number" ? 600 : 400,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatResultCellValue(value)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DataTableFrame>
      {visibleRows.length < rows.length ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
          Showing {visibleRows.length} of {rows.length} rows.
        </Typography>
      ) : null}
    </Box>
  );
}
