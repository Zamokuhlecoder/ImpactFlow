import { lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, BarChart3, Database, ShieldCheck, UsersRound, Workflow } from 'lucide-react'
import { getDashboardSnapshot } from '../services/dashboard'
import { getProgrammePerformance, getProvincialPerformance } from '../services/warehouse'
import { KpiCard } from './KpiCard'
import { ChartErrorBoundary } from './ChartErrorBoundary'

const LazyDashboardCharts = lazy(() => import('./DashboardCharts'))

const numberFormatter = new Intl.NumberFormat('en-ZA')

export function AnalyticsWorkspace({ days }: { days: number }) {
  const query = useQuery({
    queryKey: ['dashboard-snapshot', days],
    queryFn: () => getDashboardSnapshot(days),
    retry: false,
  })
  const programmeQuery = useQuery({
    queryKey: ['warehouse-programme-performance'],
    queryFn: getProgrammePerformance,
    retry: false,
  })
  const provincialQuery = useQuery({
    queryKey: ['warehouse-provincial-performance'],
    queryFn: getProvincialPerformance,
    retry: false,
  })
  const result = query.data
  const snapshot = result?.snapshot

  return <div className="page-enter operations-workspace analytics-workspace">
    <div className="page-header">
      <div><div className="eyebrow"><span className="eyebrow-line" /> INTELLIGENCE / PERFORMANCE</div><h1>Analytics<span className="heading-period">.</span></h1><p>Programme delivery and data operations from the connected database.</p></div>
      <span className="preview-pill">{query.isSuccess ? 'LIVE API DATA' : 'DATABASE DATA'}</span>
    </div>
    {query.isError && <div className="ingestion-message" role="alert">Analytics could not be loaded from the database API.</div>}
    {query.isLoading && <div className="panel operations-loading" aria-busy="true">Loading database analytics…</div>}
    {snapshot && <>
      <div className="analytics-context">
        <span>{result?.hasData ? 'Database records are available.' : 'The API is connected, but no business data has been recorded.'}</span>
        <span>Last {days} days · {numberFormatter.format(snapshot.executions.length)} recent executions</span>
      </div>
      <section aria-label="Analytics key performance indicators" className="kpi-grid analytics-kpi-grid">
        <KpiCard label="Programme reach" value={snapshot.metrics.beneficiaries} change={snapshot.changes.beneficiaries} description="aggregate beneficiaries" icon={UsersRound} index={0} />
        <KpiCard label="Active programmes" value={snapshot.metrics.activeProgrammes} change={snapshot.changes.activeProgrammes} description="currently active" icon={BarChart3} index={1} />
        <KpiCard label="Successful runs" value={snapshot.metrics.successfulPipelines} change={snapshot.changes.successfulPipelines} description="last 30 days" icon={Workflow} index={2} />
        <KpiCard label="Data quality" value={snapshot.metrics.qualityScore} suffix="%" change={snapshot.changes.qualityScore} description="latest recorded snapshot" icon={ShieldCheck} index={3} />
        <KpiCard label="Records in range" value={snapshot.ingestionTrend.slice(-days).reduce((sum, item) => sum + item.records, 0)} change={null} description="ingestion activity" icon={Database} index={4} />
        <KpiCard label="Active sources" value={snapshot.metrics.activeSources} change={snapshot.changes.activeSources} description="registered and active" icon={Activity} index={5} />
      </section>
      <div className="dashboard-section-title"><div><span className="section-kicker">OPERATING PERFORMANCE</span><h2>Delivery, quality and flow</h2></div><span>Charts contain API-backed records only.</span></div>
      <div className="module-grid">
        <article className="panel module-main">
          <div className="dashboard-section-title"><div><span className="section-kicker">WAREHOUSE MART</span><h2>Programme performance</h2></div><span>Silver-derived outcomes</span></div>
          {programmeQuery.isError && <div className="ingestion-message" role="alert">Programme outcome facts are unavailable.</div>}
          {programmeQuery.data?.length ? <div className="progress-list">{programmeQuery.data.map((item) => <div className="progress-item" key={`${item.programme}-${item.province}`}><div><span>{item.programme} · {item.province}</span><strong>{item.achievement_percentage ?? '—'}% <small>/ {item.actual ?? '—'} of {item.target ?? '—'}</small></strong></div><div className="progress-track"><span style={{ width: `${Math.min(item.achievement_percentage ?? 0, 100)}%` }} /></div></div>)}</div> : <p className="activity-empty">No programme outcome facts have been loaded.</p>}
        </article>
        <article className="panel module-side">
          <div className="dashboard-section-title"><div><span className="section-kicker">PROVINCIAL MART</span><h2>Participation activity</h2></div></div>
          {provincialQuery.data?.length ? <div className="feature-list">{provincialQuery.data.map((item) => <div key={item.province}><span>{item.province}</span><strong>{item.participants} participants · {item.programmes} programmes</strong></div>)}</div> : <p className="activity-empty">No participation facts have been loaded.</p>}
        </article>
      </div>
      <ChartErrorBoundary><Suspense fallback={<div className="panel operations-loading" aria-busy="true">Loading analytics charts…</div>}>
        <LazyDashboardCharts
          days={days}
          mode="api"
          snapshot={snapshot}
          visibleIngestion={snapshot.ingestionTrend.slice(-days)}
        />
      </Suspense></ChartErrorBoundary>
    </>}
  </div>
}
