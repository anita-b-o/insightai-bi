import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppFooter } from "./app-footer";

describe("AppFooter", () => {
  it("renders the Pampa Software credit as a safe external link", () => {
    render(<AppFooter />);

    expect(screen.getByText("Developed by", { exact: false }).closest("footer")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Pampa Software" })).toHaveAttribute(
      "href",
      "https://pampasoftware.com.ar/",
    );
    expect(screen.getByRole("link", { name: "Pampa Software" })).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "Pampa Software" })).toHaveAttribute("rel", "noopener noreferrer");
  });
});
