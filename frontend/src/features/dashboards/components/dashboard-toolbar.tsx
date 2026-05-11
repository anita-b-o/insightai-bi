import type { ReactNode } from "react";
import { Button, Stack, TextField } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { Toolbar } from "@next/components/ui/toolbar";

export function DashboardToolbar({
  name,
  onNameChange,
  onCreate,
  isCreating = false,
  detailActions,
}: {
  name?: string;
  onNameChange?: (value: string) => void;
  onCreate?: () => void;
  isCreating?: boolean;
  detailActions?: ReactNode;
}) {
  return (
    <Toolbar>
      {typeof name === "string" && onNameChange && onCreate ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} sx={{ flex: 1, minWidth: 0 }}>
          <TextField
            size="small"
            label="New dashboard"
            value={name}
            onChange={(event) => onNameChange(event.target.value.slice(0, 255))}
            sx={{ minWidth: { xs: 0, sm: 280 } }}
          />
          <Button variant="contained" onClick={onCreate} disabled={isCreating}>
            {isCreating ? "Creating..." : "Create dashboard"}
          </Button>
          <Button component={RouterLink} to="/datasets" variant="outlined">
            Browse datasets
          </Button>
        </Stack>
      ) : null}
      {detailActions}
    </Toolbar>
  );
}
