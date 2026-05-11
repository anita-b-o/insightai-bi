import PictureAsPdfRoundedIcon from "@mui/icons-material/PictureAsPdfRounded";
import { Button } from "@mui/material";
import { useState } from "react";

import type { DashboardDetail, DashboardNarrative } from "@next/features/dashboards/types";

export function ExportDashboardButton({
  dashboard,
  narrative,
  widgetsContainer,
}: {
  dashboard: DashboardDetail;
  narrative: DashboardNarrative | null;
  widgetsContainer: HTMLElement | null;
}) {
  const [isExporting, setIsExporting] = useState(false);

  async function handleExport() {
    setIsExporting(true);
    try {
      const module = await import("../export/export-dashboard");
      await module.exportDashboard({
        dashboard,
        narrative,
        widgetsContainer,
      });
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <Button variant="outlined" startIcon={<PictureAsPdfRoundedIcon />} onClick={() => void handleExport()} disabled={isExporting}>
      {isExporting ? "Exporting..." : "Export PDF"}
    </Button>
  );
}
