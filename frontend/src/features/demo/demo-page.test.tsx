import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@next/features/dashboards/components/dashboard-grid", () => ({
  DashboardGrid: ({ widgets, renderWidget }: { widgets: Array<{ id: number }>; renderWidget: (widget: { id: number }) => unknown }) => (
    <div data-testid="demo-dashboard-grid">
      {widgets.map((widget) => (
        <div key={widget.id}>{renderWidget(widget)}</div>
      ))}
    </div>
  ),
}));

import { NextDemoPage } from "@next/pages/demo-page";

describe("NextDemoPage", () => {
  it("renders the demo experience without authentication", () => {
    render(
      <MemoryRouter>
        <NextDemoPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "InsightAI BI Demo" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ask AI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Top insights" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demo dashboard" })).toBeInTheDocument();
    expect(screen.getByTestId("demo-dashboard-grid")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create account" })).toBeInTheDocument();
  }, 10_000);
});
