import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getApiErrorMessage } from "@next/core/api/errors";

import {
  createDashboard,
  createDashboardWidget,
  listDashboards,
} from "../api";
import type { CreateDashboardPayload, CreateDashboardWidgetPayload, DashboardSummary } from "../types";

interface SaveToDashboardDialogProps {
  open: boolean;
  title: string;
  payload: CreateDashboardWidgetPayload | null;
  datasetId?: number;
  defaultDashboardName?: string;
  onClose: () => void;
}

export function SaveToDashboardDialog({
  open,
  title,
  payload,
  datasetId,
  defaultDashboardName,
  onClose,
}: SaveToDashboardDialogProps) {
  const navigate = useNavigate();
  const [dashboards, setDashboards] = useState<DashboardSummary[]>([]);
  const [selectedDashboardId, setSelectedDashboardId] = useState<number | "new" | "">("");
  const [newDashboardName, setNewDashboardName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);

  function hasUsefulData(widgetPayload: CreateDashboardWidgetPayload): boolean {
    const data = widgetPayload.data_json;
    if (Array.isArray(data)) {
      return data.length > 0;
    }
    if (data && typeof data === "object") {
      return Object.keys(data).length > 0;
    }
    return false;
  }

  function validatePayload(widgetPayload: CreateDashboardWidgetPayload): string | null {
    if (widgetPayload.source_type === "query" && !(widgetPayload.query_sql?.trim())) {
      return "This query widget cannot be saved because it has no SQL to refresh later.";
    }

    if (!hasUsefulData(widgetPayload)) {
      return "This widget cannot be saved because it has no usable data yet.";
    }

    if (selectedDashboardId === "new" && !(newDashboardName.trim() || defaultDashboardName?.trim())) {
      return "Enter a dashboard name before saving.";
    }

    if (selectedDashboardId === "") {
      return "Select a dashboard before saving.";
    }

    return null;
  }

  useEffect(() => {
    if (!open) {
      return;
    }
    let isMounted = true;

    async function loadDashboards() {
      setIsBootstrapping(true);
      try {
        const items = await listDashboards();
        if (!isMounted) {
          return;
        }
        setDashboards(items);
        setSelectedDashboardId(items[0]?.id ?? "new");
      } catch (loadError: unknown) {
        if (isMounted) {
          setError(getApiErrorMessage(loadError, "Could not load dashboards"));
        }
      } finally {
        if (isMounted) {
          setIsBootstrapping(false);
        }
      }
    }

    setError(null);
    setNewDashboardName(defaultDashboardName ?? "");
    void loadDashboards();

    return () => {
      isMounted = false;
    };
  }, [defaultDashboardName, open]);

  async function handleSave() {
    if (!payload) {
      return;
    }

    const validationError = validatePayload(payload);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      let dashboardId: number;

      if (selectedDashboardId === "new") {
        const createPayload: CreateDashboardPayload = {
          name: newDashboardName.trim() || defaultDashboardName || "New dashboard",
          dataset_id: datasetId ?? null,
        };
        const created = await createDashboard(createPayload);
        dashboardId = created.id;
      } else if (typeof selectedDashboardId === "number") {
        dashboardId = selectedDashboardId;
      } else {
        throw new Error("Select a dashboard first");
      }

      await createDashboardWidget(dashboardId, payload);
      onClose();
      navigate(`/dashboards/${dashboardId}`);
    } catch (saveError: unknown) {
      setError(getApiErrorMessage(saveError, "Could not save widget"));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography color="text.secondary">
            Save this analysis as a persistent widget in an existing dashboard or create a new one.
          </Typography>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <FormControl fullWidth>
            <InputLabel id="save-dashboard-select-label">Dashboard</InputLabel>
            <Select
              labelId="save-dashboard-select-label"
              label="Dashboard"
              value={selectedDashboardId}
              onChange={(event) => {
                const value = event.target.value;
                setSelectedDashboardId(value === "new" ? "new" : Number(value));
              }}
            >
              {dashboards.map((dashboard) => (
                <MenuItem key={dashboard.id} value={dashboard.id}>
                  {dashboard.name}
                </MenuItem>
              ))}
              <MenuItem value="new">Create new dashboard</MenuItem>
            </Select>
          </FormControl>

          {selectedDashboardId === "new" ? (
            <TextField
              label="New dashboard name"
              value={newDashboardName}
              onChange={(event) => setNewDashboardName(event.target.value.slice(0, 255))}
              fullWidth
            />
          ) : null}

          {isBootstrapping ? (
            <Typography variant="body2" color="text.secondary">
              Loading dashboards...
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        {!isBootstrapping ? (
          <Button onClick={handleSave} variant="contained" disabled={isLoading || !payload}>
            Save widget
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
