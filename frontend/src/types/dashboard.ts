export type PipelineStatus = 'Succeeded' | 'Running' | 'Failed'

export interface DashboardSnapshot {
  metrics: {
    totalRecords: number
    activeSources: number
    successfulPipelines: number
    qualityScore: number
    beneficiaries: number
    activeProgrammes: number
  }
  changes: {
    totalRecords: number
    activeSources: number
    successfulPipelines: number
    qualityScore: number
    beneficiaries: number
    activeProgrammes: number
  }
  ingestionTrend: Array<{ day: string; records: number }>
  pipelineRuns: Array<{ day: string; succeeded: number; running: number; failed: number }>
  pipelineStatus: Array<{ name: string; value: number; color: string }>
  programmePerformance: Array<{ programme: string; achievement: number; target: number }>
  qualityTrend: Array<{ day: string; score: number }>
  provincialReach: Array<{ province: string; beneficiaries: number }>
  executions: Array<{
    id: string
    name: string
    source: string
    executedAt: string
    records: number
    duration: string
    durationSeconds: number
    status: PipelineStatus
  }>
  activities: Array<{ id: string; title: string; detail: string; time: string; tone: 'success' | 'warning' | 'info' }>
}
