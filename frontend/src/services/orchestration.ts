import { apiClient } from './api'

export interface OrchestrationSummary {
  total_dags: number
  active_dags: number
  running_runs: number
  successful_runs: number
  failed_runs: number
  scheduled_runs: number
  available: boolean
  message: string | null
}

export interface OrchestrationDag {
  dag_id: string
  description: string | null
  schedule: string | null
  is_paused: boolean
}

export interface OrchestrationRun {
  id: string
  airflow_dag_id: string
  airflow_run_id: string
  status: string
  trigger_type: string
  execution_date: string
  started_at: string | null
  completed_at: string | null
  records_processed: number
  records_accepted: number
  records_rejected: number
  retry_count: number
  error_details: string | null
}

export async function getOrchestrationSummary(): Promise<OrchestrationSummary> {
  const { data } = await apiClient.get<OrchestrationSummary>('/orchestration/monitoring/summary')
  return data
}

export async function getOrchestrationDags(): Promise<OrchestrationDag[]> {
  const { data } = await apiClient.get<OrchestrationDag[]>('/orchestration/dags')
  return data
}

export async function getOrchestrationRuns(): Promise<OrchestrationRun[]> {
  const { data } = await apiClient.get<OrchestrationRun[]>('/orchestration/runs')
  return data
}

export async function triggerOrchestrationDag(dagId: string): Promise<OrchestrationRun> {
  const { data } = await apiClient.post<{ orchestration_run: OrchestrationRun }>(
    `/orchestration/dags/${encodeURIComponent(dagId)}/trigger`,
    { conf: {} },
  )
  return data.orchestration_run
}
