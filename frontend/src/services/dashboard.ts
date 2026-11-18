import { apiClient } from './api'
import type { DashboardSnapshot, PipelineStatus } from '../types/dashboard'

export interface ApiDashboardSnapshot {
  has_data: boolean
  metrics: {
    total_records: number
    total_sources: number
    active_sources: number
    successful_pipelines: number
    quality_score: number
    beneficiaries: number
    total_programmes: number
    active_programmes: number
  }
  changes: {
    total_records: number | null
    active_sources: number | null
    successful_pipelines: number | null
    quality_score: number | null
    beneficiaries: number | null
    active_programmes: number | null
  }
  ingestion_trend: Array<{ day: string; records: number }>
  pipeline_runs: Array<{ day: string; succeeded: number; running: number; warning: number; failed: number }>
  pipeline_status: Array<{ name: PipelineStatus; value: number; color: string }>
  programme_performance: Array<{ programme: string; achievement: number; target: number }>
  quality_trend: Array<{ day: string; score: number }>
  provincial_reach: Array<{ province: string; beneficiaries: number }>
  executions: Array<{
    id: string
    name: string
    source: string
    executed_at: string
    records: number
    duration: string
    duration_seconds: number
    status: PipelineStatus
  }>
  activities: DashboardSnapshot['activities']
}

export function mapDashboardSnapshot(data: ApiDashboardSnapshot): DashboardSnapshot {
  return {
    metrics: {
      totalRecords: data.metrics.total_records,
      totalSources: data.metrics.total_sources,
      activeSources: data.metrics.active_sources,
      successfulPipelines: data.metrics.successful_pipelines,
      qualityScore: data.metrics.quality_score,
      beneficiaries: data.metrics.beneficiaries,
      totalProgrammes: data.metrics.total_programmes,
      activeProgrammes: data.metrics.active_programmes,
    },
    changes: {
      totalRecords: data.changes.total_records,
      activeSources: data.changes.active_sources,
      successfulPipelines: data.changes.successful_pipelines,
      qualityScore: data.changes.quality_score,
      beneficiaries: data.changes.beneficiaries,
      activeProgrammes: data.changes.active_programmes,
    },
    ingestionTrend: data.ingestion_trend,
    pipelineRuns: data.pipeline_runs,
    pipelineStatus: data.pipeline_status,
    programmePerformance: data.programme_performance,
    qualityTrend: data.quality_trend,
    provincialReach: data.provincial_reach,
    executions: data.executions.map((run) => ({
      id: run.id,
      name: run.name,
      source: run.source,
      executedAt: run.executed_at,
      records: run.records,
      duration: run.duration,
      durationSeconds: run.duration_seconds,
      status: run.status,
    })),
    activities: data.activities,
  }
}

export async function checkApiReadiness(): Promise<{ status: string; database: string }> {
  const { data } = await apiClient.get<{ status: string; database: string }>('/health/ready')
  return data
}

export async function getDashboardSnapshot(
  days: number,
): Promise<{ hasData: boolean; snapshot: DashboardSnapshot }> {
  const { data } = await apiClient.get<ApiDashboardSnapshot>('/dashboard/snapshot', {
    params: { days },
  })
  return { hasData: data.has_data, snapshot: mapDashboardSnapshot(data) }
}
