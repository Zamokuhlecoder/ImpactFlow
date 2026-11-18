import { describe, expect, it, vi } from 'vitest'
import { apiClient } from './api'
import { checkApiReadiness, mapDashboardSnapshot, type ApiDashboardSnapshot } from './dashboard'

const apiSnapshot: ApiDashboardSnapshot = {
  has_data: true,
  metrics: {
    total_records: 1250,
    total_sources: 4,
    active_sources: 2,
    successful_pipelines: 4,
    quality_score: 97.5,
    beneficiaries: 310,
    total_programmes: 5,
    active_programmes: 3,
  },
  changes: {
    total_records: null,
    active_sources: 0,
    successful_pipelines: null,
    quality_score: 2.5,
    beneficiaries: null,
    active_programmes: 0,
  },
  ingestion_trend: [{ day: '12 Nov', records: 1250 }],
  pipeline_runs: [{ day: '12 Nov', succeeded: 1, running: 0, warning: 1, failed: 0 }],
  pipeline_status: [{ name: 'Warning', value: 1, color: '#FACC15' }],
  programme_performance: [{ programme: 'Learning Support', achievement: 80, target: 100 }],
  quality_trend: [{ day: '12 Nov', score: 97.5 }],
  provincial_reach: [{ province: 'Gauteng', beneficiaries: 310 }],
  executions: [{
    id: 'run-1',
    name: 'Aggregate import',
    source: 'CSV',
    executed_at: '2026-11-12T10:00:00Z',
    records: 1250,
    duration: '20s',
    duration_seconds: 20,
    status: 'Warning',
  }],
  activities: [{ id: 'activity-1', title: 'Import completed', detail: '1 warning', time: 'now', tone: 'warning' }],
}

describe('mapDashboardSnapshot', () => {
  it('maps API field names and preserves warning pipeline statuses', () => {
    const snapshot = mapDashboardSnapshot(apiSnapshot)

    expect(snapshot.metrics.totalRecords).toBe(1250)
    expect(snapshot.metrics.totalSources).toBe(4)
    expect(snapshot.metrics.totalProgrammes).toBe(5)
    expect(snapshot.changes.totalRecords).toBeNull()
    expect(snapshot.pipelineRuns[0].warning).toBe(1)
    expect(snapshot.executions[0]).toEqual({
      id: 'run-1',
      name: 'Aggregate import',
      source: 'CSV',
      executedAt: '2026-11-12T10:00:00Z',
      records: 1250,
      duration: '20s',
      durationSeconds: 20,
      status: 'Warning',
    })

    expect(snapshot.executions[0]).not.toHaveProperty('executed_at')
  })
})

describe('checkApiReadiness', () => {
  it('returns the readiness response for the query cache', async () => {
    const readiness = { status: 'ready', database: 'connected' }
    const request = vi.spyOn(apiClient, 'get').mockResolvedValueOnce({ data: readiness })
    try {
      expect(await checkApiReadiness()).toEqual(readiness)
      expect(request).toHaveBeenCalledWith('/health/ready')
    } finally {
      request.mockRestore()
    }
  })
})
