import { nextApiClient } from "@next/core/api/client";

export interface DatasetColumnDto {
  id: number;
  name: string;
  position: number;
  inferred_type: string;
  nullable: boolean;
  distinct_count: number | null;
  sample_value: string | null;
}

export interface DatasetSummaryDto {
  id: number;
  name: string;
  description: string | null;
  original_filename: string;
  row_count: number;
  column_count: number;
  created_at: string;
}

export interface DatasetDetailDto extends DatasetSummaryDto {
  file_size_bytes: number;
  columns: DatasetColumnDto[];
}

export async function listDatasets(): Promise<DatasetSummaryDto[]> {
  const { data } = await nextApiClient.get<DatasetSummaryDto[]>("/datasets");
  return data;
}

export async function getDataset(datasetId: number): Promise<DatasetDetailDto> {
  const { data } = await nextApiClient.get<DatasetDetailDto>(`/datasets/${datasetId}`);
  return data;
}

export async function uploadDataset(formData: FormData): Promise<DatasetDetailDto> {
  const { data } = await nextApiClient.post<DatasetDetailDto>("/datasets/upload", formData);
  return data;
}
