import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { PageHeader } from "@next/components/ui/page-header";
import { PageSurface } from "@next/components/ui/page-surface";
import { OpenSection } from "@next/components/ui/surface-card";
import { getApiErrorMessage } from "@next/core/api/errors";
import { useUploadDataset } from "@next/features/datasets/hooks";

export function NextUploadPage() {
  const navigate = useNavigate();
  const uploadMutation = useUploadDataset();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select a CSV file");
      return;
    }

    setError(null);
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("description", description);
      formData.append("file", file);
      const dataset = await uploadMutation.mutateAsync(formData);
      navigate(`/datasets/${dataset.id}`);
    } catch (submissionError: unknown) {
      setError(getApiErrorMessage(submissionError, "Upload failed"));
    }
  }

  return (
    <PageSurface>
      <Stack spacing={3}>
        <PageHeader
          eyebrow="Dataset ingestion"
          title="Upload dataset"
          description="Send a CSV to the existing API, generate a schema profile, and prepare it for Ask AI and dashboards."
        />
        <OpenSection divider="both" spacing={1.5} sx={{ maxWidth: 780 }}>
          <Stack component="form" spacing={2} onSubmit={handleSubmit}>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField label="Dataset name" value={name} onChange={(event) => setName(event.target.value)} required />
            <TextField
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              multiline
              minRows={4}
            />
            <Stack spacing={0.75}>
              <Typography variant="subtitle2">CSV file</Typography>
              <input
                type="file"
                accept=".csv"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
            </Stack>
            <Button type="submit" variant="contained" disabled={uploadMutation.isPending}>
              {uploadMutation.isPending ? "Uploading..." : "Upload dataset"}
            </Button>
          </Stack>
        </OpenSection>
      </Stack>
    </PageSurface>
  );
}
