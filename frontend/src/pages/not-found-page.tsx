import { Button, Stack } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { PageSurface } from "@next/components/ui/page-surface";
import { EmptyState } from "@next/components/ui/states";

export function NextNotFoundPage() {
  return (
    <PageSurface>
      <EmptyState
        title="Page not found"
        description="The route does not exist in this frontend."
        action={
          <Stack direction="row" spacing={1.5}>
            <Button component={RouterLink} to="/datasets" variant="contained">
              Go to datasets
            </Button>
            <Button component={RouterLink} to="/demo" variant="outlined">
              Open demo
            </Button>
          </Stack>
        }
      />
    </PageSurface>
  );
}
