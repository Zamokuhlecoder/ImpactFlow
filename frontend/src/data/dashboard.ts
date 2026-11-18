import type { DashboardSnapshot, PipelineStatus } from '../types/dashboard'

const provinces = [
  'Eastern Cape',
  'Free State',
  'Gauteng',
  'KwaZulu-Natal',
  'Limpopo',
  'Mpumalanga',
  'Northern Cape',
  'North West',
  'Western Cape',
]

const programmes = [
  'Youth Employment',
  'Learning Support',
  'Community Health',
  'Skills for Work',
]

function randomGenerator(seed: number) {
  let state = seed >>> 0

  return () => {
    state += 0x6d2b79f5
    let value = state
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

function formatDay(daysAgo: number, referenceDate: Date) {
  const date = new Date(referenceDate)
  date.setDate(date.getDate() - daysAgo)
  return new Intl.DateTimeFormat('en-ZA', { day: '2-digit', month: 'short' }).format(date)
}

function formatTime(hoursAgo: number, referenceDate: Date) {
  const date = new Date(referenceDate)
  date.setHours(date.getHours() - hoursAgo)
  return date.toISOString()
}

export function createDashboardSnapshot(seed = 2026, referenceDate = new Date()): DashboardSnapshot {
  const random = randomGenerator(seed)
  const statuses: PipelineStatus[] = ['Succeeded', 'Succeeded', 'Running', 'Failed']
  const sources = ['Beneficiary Registry', 'School Attendance', 'Programme Outcomes', 'Health Outreach', 'Youth Placement Register', 'Expenditure Register', 'Field Surveys', 'Programme Outcomes']
  const executionNames = [
    'Beneficiary registry sync',
    'Attendance consolidation',
    'Monthly outcomes model',
    'Community health import',
    'Youth placement updates',
    'Expenditure reconciliation',
    'Field survey validation',
    'Programme indicator refresh',
  ]

  const executions = executionNames.map((name, index) => {
    const records = Math.round(1200 + random() * 16800)
    const durationSeconds = Math.floor(60 + random() * 480)
    return {
      id: `run-${seed}-${index}`,
      name,
      source: sources[index],
      executedAt: formatTime(index * 2 + 1, referenceDate),
      records,
      duration: `${Math.floor(durationSeconds / 60)}m ${durationSeconds % 60}s`,
      durationSeconds,
      status: statuses[Math.floor(random() * statuses.length)],
    }
  })

  const pipelineRuns = Array.from({ length: 90 }, (_, index) => ({
    day: formatDay(89 - index, referenceDate),
    succeeded: Math.floor(4 + random() * 8),
    running: Math.floor(random() * 3),
    warning: Math.floor(random() * 2),
    failed: Math.floor(random() * 2),
  }))
  const recentRuns = pipelineRuns.slice(-30)
  const totalSucceeded = recentRuns.reduce((sum, item) => sum + item.succeeded, 0)
  const totalRunning = recentRuns.reduce((sum, item) => sum + item.running, 0)
  const totalWarning = recentRuns.reduce((sum, item) => sum + item.warning, 0)
  const totalFailed = recentRuns.reduce((sum, item) => sum + item.failed, 0)
  const previousSucceeded = pipelineRuns.slice(-60, -30).reduce((sum, item) => sum + item.succeeded, 0)
  const qualityTrend = Array.from({ length: 12 }, (_, index) => ({
    day: formatDay((11 - index) * 7, referenceDate),
    score: Number((91 + random() * 7.5).toFixed(1)),
  }))
  const provincialReach = provinces.map((province) => ({
    province,
    beneficiaries: Math.round(1600 + random() * 2200),
  }))
  const totalRecords = 1283400 + Math.floor(random() * 18000)
  const activeSources = 12 + Math.floor(random() * 4)
  const beneficiaries = provincialReach.reduce((sum, item) => sum + item.beneficiaries, 0)
  const percentChange = (current: number, previous: number) => Number((((current - previous) / previous) * 100).toFixed(1))
  const attendance = executions[1]

  return {
    metrics: {
      totalRecords,
      totalSources: activeSources,
      activeSources,
      successfulPipelines: totalSucceeded,
      qualityScore: qualityTrend[qualityTrend.length - 1].score,
      beneficiaries,
      totalProgrammes: 8,
      activeProgrammes: 8,
    },
    changes: {
      totalRecords: percentChange(totalRecords, totalRecords - Math.round(30000 + random() * 40000)),
      activeSources: percentChange(activeSources, activeSources - 1),
      successfulPipelines: percentChange(totalSucceeded, previousSucceeded),
      qualityScore: percentChange(qualityTrend[11].score, qualityTrend[10].score),
      beneficiaries: percentChange(beneficiaries, beneficiaries - Math.round(400 + random() * 600)),
      activeProgrammes: percentChange(8, 7),
    },
    ingestionTrend: Array.from({ length: 90 }, (_, index) => ({
      day: formatDay(89 - index, referenceDate),
      records: Math.round(4000 + random() * 6500 + Math.sin(index / 3) * 2000),
    })),
    pipelineRuns,
    pipelineStatus: [
      { name: 'Succeeded', value: totalSucceeded, color: '#22C55E' },
      { name: 'Running', value: totalRunning, color: '#FACC15' },
      { name: 'Warning', value: totalWarning, color: '#FACC15' },
      { name: 'Failed', value: totalFailed, color: '#F43F5E' },
    ],
    programmePerformance: programmes.map((programme) => ({
      programme,
      achievement: Math.round(68 + random() * 29),
      target: 100,
    })),
    qualityTrend,
    provincialReach,
    executions,
    activities: [
      { id: 'activity-1', title: `Attendance consolidation ${attendance.status.toLowerCase()}`, detail: `${new Intl.NumberFormat('en-ZA').format(attendance.records)} records processed`, time: '3 hours ago', tone: attendance.status === 'Succeeded' ? 'success' : attendance.status === 'Failed' ? 'warning' : 'info' },
      { id: 'activity-2', title: 'Validation warning detected', detail: '3.2% missing location codes', time: '46 min ago', tone: 'warning' },
      { id: 'activity-3', title: 'New source connected', detail: 'Youth placement register', time: '2 hours ago', tone: 'info' },
    ],
  }
}
