import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

import { reportClientError } from "@next/app/client-error-reporting";
import type { DashboardDetail, DashboardNarrative } from "@next/features/dashboards/types";

interface ExportDashboardOptions {
  dashboard: DashboardDetail;
  narrative: DashboardNarrative | null;
  widgetsContainer: HTMLElement | null;
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}

function toList(items: string[], limit: number): string {
  if (!items.length) {
    return "";
  }
  return items
    .slice(0, limit)
    .map((item) => `• ${item}`)
    .join("\n");
}

function stripInteractiveElements(root: HTMLElement) {
  root.querySelectorAll("button, input, textarea, select, [role='button']").forEach((element) => {
    element.remove();
  });
}

function normalizeWidgetsForExport(root: HTMLElement) {
  const gridLayout = root.querySelector(".dashboard-grid-layout") as HTMLElement | null;
  if (gridLayout) {
    gridLayout.style.height = "auto";
    gridLayout.style.display = "grid";
    gridLayout.style.gridTemplateColumns = "repeat(2, minmax(0, 1fr))";
    gridLayout.style.gap = "24px";
    gridLayout.style.position = "static";
  }

  root.querySelectorAll<HTMLElement>(".react-grid-item").forEach((item) => {
    item.style.position = "static";
    item.style.transform = "none";
    item.style.width = "auto";
    item.style.height = "auto";
    item.style.left = "auto";
    item.style.top = "auto";
    item.style.margin = "0";
  });

  root.querySelectorAll<HTMLElement>(".react-resizable-handle").forEach((handle) => {
    handle.remove();
  });

  root.querySelectorAll<HTMLElement>(".recharts-responsive-container").forEach((container) => {
    container.style.width = "100%";
    container.style.height = "300px";
    container.style.minHeight = "300px";
  });

  root.querySelectorAll<HTMLElement>(".MuiTableContainer-root").forEach((tableFrame) => {
    tableFrame.style.maxHeight = "none";
    tableFrame.style.height = "auto";
    tableFrame.style.overflow = "visible";
  });
}

function buildReportElement({ dashboard, narrative, widgetsContainer }: ExportDashboardOptions): HTMLDivElement {
  const exportDate = new Date().toLocaleString();
  const failedWidgets = dashboard.widgets.filter((widget) => widget.execution_status === "failed");

  const root = document.createElement("div");
  root.style.position = "fixed";
  root.style.left = "-20000px";
  root.style.top = "0";
  root.style.width = "1240px";
  root.style.padding = "32px";
  root.style.background = "#f3f7fc";
  root.style.color = "#0f172a";
  root.style.fontFamily = "\"Inter\", \"Segoe UI\", sans-serif";
  root.style.lineHeight = "1.5";
  root.style.zIndex = "-1";

  const header = document.createElement("div");
  header.style.marginBottom = "24px";
  header.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:16px;">
      <div>
        <div style="font-size:30px;font-weight:700;margin-bottom:4px;">${dashboard.name}</div>
        <div style="font-size:14px;color:#475569;">Dashboard export</div>
      </div>
      <div style="text-align:right;font-size:13px;color:#475569;">
        <div>Exported: ${exportDate}</div>
        <div>Freshness: ${dashboard.freshness_status.replace(/_/g, " ")}</div>
        <div>Last successful refresh: ${formatDateTime(dashboard.last_successful_refresh_at)}</div>
      </div>
    </div>
  `;
  root.appendChild(header);

  const summary = document.createElement("div");
  summary.style.border = "1px solid #c6d8ee";
  summary.style.borderRadius = "16px";
  summary.style.padding = "24px";
  summary.style.marginBottom = "20px";
  summary.style.background = "linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0ea5e9 100%)";
  summary.style.color = "#f8fafc";
  summary.innerHTML = `
    <div style="font-size:12px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;color:rgba(248,250,252,0.72);">Dashboard narrative</div>
    <div style="font-size:24px;font-weight:700;margin-bottom:12px;">Current interpretation</div>
    <div style="font-size:14px;color:rgba(248,250,252,0.84);white-space:pre-wrap;">
      ${narrative?.summary?.trim() || "No narrative summary was available at export time. The report includes the current dashboard state and widget outputs."}
    </div>
    ${
      narrative?.key_findings?.length
        ? `<div style="margin-top:16px;">
             <div style="font-size:15px;font-weight:600;margin-bottom:8px;">Key findings</div>
             <div style="font-size:14px;color:rgba(248,250,252,0.84);white-space:pre-wrap;">${toList(narrative.key_findings, 5)}</div>
           </div>`
        : ""
    }
  `;
  root.appendChild(summary);

  if (narrative?.risks_or_caveats?.length) {
    const caveats = document.createElement("div");
    caveats.style.border = "1px solid #fbbf24";
    caveats.style.background = "#fffbeb";
    caveats.style.borderRadius = "12px";
    caveats.style.padding = "16px 20px";
    caveats.style.marginBottom = "20px";
    caveats.innerHTML = `
      <div style="font-size:16px;font-weight:600;margin-bottom:8px;">Caveats</div>
      <div style="font-size:14px;color:#92400e;white-space:pre-wrap;">${toList(narrative.risks_or_caveats, 5)}</div>
    `;
    root.appendChild(caveats);
  }

  if (failedWidgets.length > 0 || dashboard.freshness_status === "failed") {
    const warning = document.createElement("div");
    warning.style.border = "1px solid #f87171";
    warning.style.background = "#fff1f2";
    warning.style.borderRadius = "12px";
    warning.style.padding = "16px 20px";
    warning.style.marginBottom = "20px";
    warning.innerHTML = `
      <div style="font-size:16px;font-weight:600;margin-bottom:8px;">Warnings</div>
      <div style="font-size:14px;color:#9f1239;white-space:pre-wrap;">
        ${
          failedWidgets.length
            ? toList(
                failedWidgets.map((widget) => `${widget.title ?? "Widget"} failed${widget.error_message ? `: ${widget.error_message}` : "."}`),
                6,
              )
            : "• The dashboard freshness status is failed. Review widget execution results before using this report as final output."
        }
      </div>
    `;
    root.appendChild(warning);
  }

  const widgetsSection = document.createElement("div");
  widgetsSection.style.border = "1px solid #d7e4f2";
  widgetsSection.style.borderRadius = "16px";
  widgetsSection.style.padding = "24px";
  widgetsSection.style.background = "#ffffff";
  widgetsSection.innerHTML = `<div style="font-size:20px;font-weight:600;margin-bottom:16px;">Widgets</div>`;

  if (!dashboard.widgets.length) {
    const emptyState = document.createElement("div");
    emptyState.style.fontSize = "14px";
    emptyState.style.color = "#475569";
    emptyState.textContent = "This dashboard has no widgets yet. The export contains metadata and narrative only.";
    widgetsSection.appendChild(emptyState);
  } else if (widgetsContainer) {
    const widgetClone = widgetsContainer.cloneNode(true) as HTMLElement;
    stripInteractiveElements(widgetClone);
    normalizeWidgetsForExport(widgetClone);
    widgetClone.style.width = "100%";
    widgetsSection.appendChild(widgetClone);
  } else {
    const fallback = document.createElement("div");
    fallback.style.fontSize = "14px";
    fallback.style.color = "#475569";
    fallback.textContent = "Widget content was not available in the current view, so only dashboard metadata could be exported.";
    widgetsSection.appendChild(fallback);
  }

  root.appendChild(widgetsSection);
  return root;
}

function addCanvasToPdf(pdf: jsPDF, canvas: HTMLCanvasElement) {
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 10;
  const contentWidth = pageWidth - margin * 2;
  const scaledHeight = (canvas.height * contentWidth) / canvas.width;

  let renderedHeight = 0;
  let pageIndex = 0;

  while (renderedHeight < scaledHeight) {
    if (pageIndex > 0) {
      pdf.addPage();
    }

    const sourceY = (renderedHeight * canvas.width) / contentWidth;
    const sourceHeight = Math.min(((pageHeight - margin * 2) * canvas.width) / contentWidth, canvas.height - sourceY);
    const pageCanvas = document.createElement("canvas");
    pageCanvas.width = canvas.width;
    pageCanvas.height = sourceHeight;
    const context = pageCanvas.getContext("2d");
    if (!context) {
      throw new Error("Could not prepare PDF canvas context");
    }
    context.drawImage(canvas, 0, sourceY, canvas.width, sourceHeight, 0, 0, canvas.width, sourceHeight);

    const pageImageHeight = (pageCanvas.height * contentWidth) / pageCanvas.width;
    pdf.addImage(pageCanvas.toDataURL("image/png"), "PNG", margin, margin, contentWidth, pageImageHeight);

    renderedHeight += pageImageHeight;
    pageIndex += 1;
  }
}

export async function exportDashboard(options: ExportDashboardOptions): Promise<void> {
  const reportElement = buildReportElement(options);
  document.body.appendChild(reportElement);

  try {
    const canvas = await html2canvas(reportElement, {
      backgroundColor: "#ffffff",
      scale: 2,
      useCORS: true,
      logging: false,
    });
    const pdf = new jsPDF("p", "mm", "a4");
    addCanvasToPdf(pdf, canvas);
    const safeName = options.dashboard.name.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "") || "dashboard";
    pdf.save(`${safeName}.pdf`);
  } catch (error) {
    void reportClientError({
      category: "pdf_export_failed",
      message: error instanceof Error ? error.message : "Dashboard export failed",
      metadata: {
        dashboardId: options.dashboard.id,
        dashboardName: options.dashboard.name,
      },
    });
    throw error;
  } finally {
    reportElement.remove();
  }
}
