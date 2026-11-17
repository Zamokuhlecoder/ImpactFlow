import { describe, expect, it } from 'vitest'
import { createDashboardSnapshot } from './dashboard'

describe('createDashboardSnapshot', () => {
  it('creates repeatable demonstration data for a fixed seed', () => {
    const referenceDate = new Date('2026-11-17T12:00:00Z')

    expect(createDashboardSnapshot(42, referenceDate)).toEqual(createDashboardSnapshot(42, referenceDate))
  })

  it('includes all nine provinces and pipeline execution history', () => {
    const snapshot = createDashboardSnapshot(42, new Date('2026-11-17T12:00:00Z'))

    expect(snapshot.provincialReach).toHaveLength(9)
    expect(snapshot.executions.length).toBeGreaterThan(0)
    expect(snapshot.executions.every((execution) => execution.records > 0)).toBe(true)
  })

  it('keeps headline totals consistent with their demonstration breakdowns', () => {
    const snapshot = createDashboardSnapshot(42, new Date('2026-11-17T12:00:00Z'))
    expect(snapshot.metrics.beneficiaries).toBe(snapshot.provincialReach.reduce((sum, item) => sum + item.beneficiaries, 0))
    expect(snapshot.metrics.successfulPipelines).toBe(snapshot.pipelineRuns.slice(-30).reduce((sum, item) => sum + item.succeeded, 0))
    expect(snapshot.metrics.qualityScore).toBe(snapshot.qualityTrend.at(-1)?.score)
    expect(snapshot.pipelineStatus.find((item) => item.name === 'Succeeded')?.value).toBe(snapshot.metrics.successfulPipelines)
  })

  it('creates sortable timestamps and numeric execution durations', () => {
    const snapshot = createDashboardSnapshot(42, new Date('2026-11-17T12:00:00Z'))

    expect(snapshot.executions[0].executedAt > snapshot.executions[1].executedAt).toBe(true)
    expect(snapshot.executions.every((run) => run.duration === `${Math.floor(run.durationSeconds / 60)}m ${run.durationSeconds % 60}s`)).toBe(true)
  })
})
