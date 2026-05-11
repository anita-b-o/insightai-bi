import { beforeEach, describe, expect, it, vi } from "vitest";

import { nextApiClient } from "@next/core/api/client";
import { uploadDataset } from "./api";

vi.mock("@next/core/api/client", () => ({
  nextApiClient: {
    post: vi.fn(),
  },
}));

describe("datasets api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts upload form data without forcing multipart headers", async () => {
    const formData = new FormData();
    formData.append("name", "Sales");
    formData.append("description", "Monthly sales");
    formData.append("file", new File(["name,amount\nAlice,10\n"], "sales.csv", { type: "text/csv" }));

    vi.mocked(nextApiClient.post).mockResolvedValue({
      data: {
        id: 1,
        name: "Sales",
        description: "Monthly sales",
        original_filename: "sales.csv",
        row_count: 1,
        column_count: 2,
        file_size_bytes: 21,
        created_at: "2026-04-30T00:00:00Z",
        columns: [],
      },
    });

    await uploadDataset(formData);

    expect(nextApiClient.post).toHaveBeenCalledWith("/datasets/upload", formData);
    const sentFormData = vi.mocked(nextApiClient.post).mock.calls[0][1] as FormData;
    expect(Array.from(sentFormData.keys())).toEqual(["name", "description", "file"]);
    expect(vi.mocked(nextApiClient.post).mock.calls[0]).toHaveLength(2);
  });
});
