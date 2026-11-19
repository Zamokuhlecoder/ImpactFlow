import { apiClient } from './api'

export type ProcessingLayer = 'bronze' | 'silver' | 'gold' | 'quarantine'

export interface ProcessingPipeline {
  name: string
  label: string
  description: string
}

export interface QualityReport {
  total_records: number
  valid_records: number
  invalid_records: number
  duplicate_records: number
  missing_values: number
  quality_percentage: number
}

export interface TransformationRun {
  id: string
  dataset_import_id: string
  dataset_id: string | null
  pipeline_name: string
  schema_type: 'aggregate' | 'participation' | 'generic'
  status: 'running' | 'succeeded' | 'failed' | 'warning'
  records_received: number
  records_processed: number
  records_rejected: number
  duplicate_records: number
  missing_values: number
  quality_score: number
  quality_report: QualityReport
  error_details: string | null
  started_at: string
  completed_at: string | null
}

export interface ProcessingDataset {
  import_id: string
  dataset_id: string | null
  dataset_name: string
  source_name: string
  schema_type: 'aggregate' | 'participation' | 'generic'
  import_status: 'running' | 'succeeded' | 'failed'
  records_received: number
  imported_at: string
  can_process: boolean
  latest_run: TransformationRun | null
}

export interface LayerDataset {
  name: string
  records: Array<Record<string, unknown>>
}

export interface LayerData {
  layer: ProcessingLayer
  datasets: LayerDataset[]
}

export async function getProcessingPipelines(): Promise<ProcessingPipeline[]> {
  return (await apiClient.get<ProcessingPipeline[]>('/processing/pipelines')).data
}

export async function getProcessingDatasets(): Promise<ProcessingDataset[]> {
  return (await apiClient.get<ProcessingDataset[]>('/processing/datasets')).data
}

export async function getTransformationRuns(): Promise<TransformationRun[]> {
  return (await apiClient.get<TransformationRun[]>('/processing/runs', {
    params: { limit: 50 },
  })).data
}

export async function getLayerData(
  importId: string,
  layer: ProcessingLayer,
): Promise<LayerData> {
  return (await apiClient.get<LayerData>(`/processing/datasets/${importId}/layers/${layer}`)).data
}

export async function startTransformation(
  datasetImportId: string,
  pipelineName: string,
): Promise<TransformationRun> {
  return (await apiClient.post<TransformationRun>('/processing/runs', {
    dataset_import_id: datasetImportId,
    pipeline_name: pipelineName,
  }, { timeout: 120_000 })).data
}
