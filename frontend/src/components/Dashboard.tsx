import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, ArrowDownRight, BarChart3, Check, Database, RefreshCw, ShieldCheck, UsersRound, Workflow } from 'lucide-react'
import { Navigate, useLocation } from 'react-router-dom'
import { createDashboardSnapshot } from '../data/dashboard'
import { modules } from '../data/navigation'
import { checkApiReadiness, getDashboardSnapshot } from '../services/dashboard'
import { ChartErrorBoundary } from './ChartErrorBoundary'
import { CsvOverview } from './CsvOverview'
import { ExecutionTable } from './ExecutionTable'
import { KpiCard } from './KpiCard'
import { ModulePage } from './ModulePage'
import { SectionHeading } from './SectionHeading'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const LazyDashboardCharts = lazy(() => import('./DashboardCharts'))
const LazyAnalyticsWorkspace = lazy(() => import('./AnalyticsWorkspace').then(module => ({ default: module.AnalyticsWorkspace })))
const LazyArchitectureWorkspace = lazy(() => import('./ArchitectureWorkspace').then(module => ({ default: module.ArchitectureWorkspace })))
const LazyDataProcessingWorkspace = lazy(() => import('./DataProcessingWorkspace').then(module => ({ default: module.DataProcessingWorkspace })))
const LazyIngestionWorkspace = lazy(() => import('./IngestionWorkspace').then(module => ({ default: module.IngestionWorkspace })))
const LazyPipelineWorkspace = lazy(() => import('./PipelineWorkspace').then(module => ({ default: module.PipelineWorkspace })))
const LazyQualityWorkspace = lazy(() => import('./QualityWorkspace').then(module => ({ default: module.QualityWorkspace })))

export default function Dashboard({ onSignOut }: { onSignOut: () => void }) {
  const { pathname } = useLocation()
  const queryClient = useQueryClient()
  const currentModule = modules.find((item) => item.path === pathname)
  const isProcessingWorkspace = pathname === '/data-processing'
  const isIngestionWorkspace = pathname === '/data-sources' || pathname === '/data-ingestion' || isProcessingWorkspace
  const isPipelineWorkspace = pathname === '/data-pipelines' || pathname === '/monitoring'
  const isAnalyticsWorkspace = pathname === '/analytics'
  const isOperationalWorkspace = isIngestionWorkspace || isPipelineWorkspace || isAnalyticsWorkspace
    || pathname === '/data-quality' || pathname === '/data-lake' || pathname === '/data-lineage'
  const [demoSnapshot, setDemoSnapshot] = useState(() => createDashboardSnapshot())
  const [seed, setSeed] = useState(2026)
  const [overviewMode, setOverviewMode] = useState<'csv' | 'api'>('api')
  const [days, setDays] = useState(30)
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [demoLastUpdated, setDemoLastUpdated] = useState(() => new Date())
  const [refreshMessage, setRefreshMessage] = useState('')
  const readinessQuery = useQuery({
    queryKey: ['api-readiness'],
    queryFn: checkApiReadiness,
    retry: false,
  })
  const dashboardQuery = useQuery({
    queryKey: ['dashboard-snapshot', days],
    queryFn: () => getDashboardSnapshot(days),
    enabled: pathname === '/' && overviewMode === 'api',
    retry: false,
  })
  const apiResult = dashboardQuery.data
  const isCsvMode = pathname === '/' && overviewMode === 'csv'
  const isApiMode = pathname === '/' && overviewMode === 'api' && apiResult !== undefined
  const snapshot = isApiMode && apiResult ? apiResult.snapshot : demoSnapshot
  const dataMode = isOperationalWorkspace ? (readinessQuery.isSuccess ? 'api' : 'unavailable') : pathname !== '/' ? 'demo' : isCsvMode ? 'csv' : isApiMode ? 'api' : 'unavailable'
  const visibleIngestion = useMemo(() => snapshot.ingestionTrend.slice(-days), [days, snapshot])

  useEffect(() => {
    document.title = `ImpactFlow | ${currentModule?.label ?? 'Overview'}`
    window.scrollTo(0, 0)
  }, [pathname, currentModule?.label])

  async function refreshSnapshot() {
    if (isOperationalWorkspace) {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['dashboard-snapshot'] }),
        queryClient.invalidateQueries({ queryKey: ['ingestion-sources'] }),
        queryClient.invalidateQueries({ queryKey: ['ingestion-datasets'] }),
        queryClient.invalidateQueries({ queryKey: ['import-history'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-datasets'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-runs'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-layer'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-pipelines'] }),
      ])
      setRefreshMessage('Database-backed workspace data refreshed.')
      return
    }
    if (pathname === '/') {
      if (isCsvMode) {
        await queryClient.invalidateQueries({ queryKey: ['worldbank-population'] })
        setRefreshMessage('Public data refresh requested. CSV data is unchanged.')
        return
      }
      const result = await dashboardQuery.refetch()
      setRefreshMessage(result.error
        ? 'Dashboard refresh failed. The last successful API snapshot remains visible when available.'
        : 'Database-backed dashboard snapshot refreshed.')
      return
    }
    const nextSeed = seed + 1
    setSeed(nextSeed)
    setDemoSnapshot(createDashboardSnapshot(nextSeed))
    setDemoLastUpdated(new Date())
    setRefreshMessage('Synthetic dashboard snapshot refreshed.')
  }

  function closeMobileNavigation() {
    setMobileOpen(false)
    if (mobileOpen) document.getElementById('mobile-nav-trigger')?.focus()
  }

  if (!currentModule) return <Navigate replace to="/" />
  const { metrics, changes } = snapshot
  const lastUpdated = isApiMode && dashboardQuery.dataUpdatedAt
    ? new Date(dashboardQuery.dataUpdatedAt)
    : demoLastUpdated
  const apiFailure = dashboardQuery.isError
  const demoNotice = pathname !== '/'
    ? 'This module is a non-operational preview. Only Overview currently reads database-backed API data.'
    : isApiMode
      ? apiFailure
        ? 'The API refresh failed. The last successful database-backed snapshot remains visible.'
        : apiResult?.hasData
          ? 'Programme reach and operational figures below come from the API.'
          : 'The API is connected, but no business data has been recorded yet. Metrics below are zero-valued database results.'
      : apiFailure
        ? 'The API request failed. Use Refresh to retry.'
        : readinessQuery.isError
          ? 'The API or database is unavailable. Check the connection and use Refresh to retry.'
          : 'Connecting to the API and loading the database-backed snapshot.'

  return (
    <div className={`app-shell${collapsed ? ' app-shell-collapsed' : ''}`}>
      <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onCloseMobile={closeMobileNavigation} onToggleCollapse={() => setCollapsed(!collapsed)} onSignOut={onSignOut} />
      <main className="main-column">
        <Topbar
          activities={pathname === '/' && isApiMode ? snapshot.activities : []}
          apiConnected={(pathname === '/' || isOperationalWorkspace) && readinessQuery.isSuccess}
          days={days}
          mobileOpen={mobileOpen}
          mode={dataMode}
          onDaysChange={setDays}
          onOpenMobileNav={() => setMobileOpen(true)}
          onRefresh={() => { void refreshSnapshot() }}
          onSearch={setSearch}
          search={search}
          showRange={(pathname === '/' && !isCsvMode) || isAnalyticsWorkspace}
          title={currentModule.label}
        />
        <div className="page-content">
          <div className="sr-only" role="status">{refreshMessage}</div>
          {pathname === '/' && <div className="source-switch" aria-label="Overview data source">
            <button aria-pressed={isCsvMode} className="button button-small" onClick={() => setOverviewMode('csv')} type="button">Browser CSV</button>
            <button aria-pressed={!isCsvMode} className="button button-small" onClick={() => setOverviewMode('api')} type="button">Database API</button>
          </div>}
          {isCsvMode ? <CsvOverview search={search} /> : pathname === '/' ? (
            <div className="page-enter">
              <div className="page-header">
                <div><div className="eyebrow"><span className="eyebrow-line" /> YOUR DATA, IN FOCUS</div><h1>Overview<span className="heading-period">.</span></h1><p>Monitor your organisation's data operations and programme performance.</p></div>
                <div className="page-header-meta"><span className="live-indicator"><span /> API WORKSPACE</span>{isApiMode && <span>Snapshot updated {new Intl.DateTimeFormat('en-ZA', { hour: '2-digit', minute: '2-digit', hour12: false }).format(lastUpdated)}</span>}</div>
              </div>
              <div className={`demo-notice${isApiMode ? ' api-notice' : ''}`} role="status">
                <span className="demo-notice-icon"><Activity size={16} /></span>
                <p><strong>{isApiMode ? 'Database-backed API data' : 'Dashboard data unavailable'}</strong><span> {demoNotice} Demo identity is not authentication; use synthetic data locally only.</span></p>
                {!isApiMode && apiFailure && <button className="demo-notice-action" onClick={() => { void refreshSnapshot() }}>Retry</button>}
              </div>
              {isApiMode && <>
              <section aria-label="Key performance indicators" className="kpi-grid">
                <KpiCard label="Total Records" value={metrics.totalRecords} change={changes.totalRecords} description="vs. previous period" icon={Database} index={0} />
                <KpiCard label="Active Data Sources" value={metrics.activeSources} change={changes.activeSources} description="vs. previous period" icon={Activity} index={1} />
                <KpiCard label="Successful Pipelines" value={metrics.successfulPipelines} change={changes.successfulPipelines} description="vs. previous 30 days" icon={Workflow} index={2} />
                <KpiCard label="Data Quality Score" value={metrics.qualityScore} suffix="%" change={changes.qualityScore} description="vs. previous week" icon={ShieldCheck} index={3} />
                <KpiCard label="Total Beneficiaries" value={metrics.beneficiaries} change={changes.beneficiaries} description="vs. previous period" icon={UsersRound} index={4} />
                <KpiCard label="Active Programmes" value={metrics.activeProgrammes} change={changes.activeProgrammes} description="vs. previous period" icon={BarChart3} index={5} />
                <KpiCard label="Registered Data Sources" value={metrics.totalSources} change={null} description="total registered" icon={Database} index={6} />
                <KpiCard label="Total Programmes" value={metrics.totalProgrammes} change={null} description="total registered" icon={BarChart3} index={7} />
              </section>
              <div className="dashboard-section-title"><div><span className="section-kicker">PERFORMANCE AT A GLANCE</span><h2>Analytics overview</h2></div><span>Selected date range applies to pipeline runs and ingestion.</span></div>
              <ChartErrorBoundary><Suspense fallback={<div className="chart-grid chart-loading" aria-busy="true" aria-label="Loading dashboard charts">{Array.from({ length: 3 }, (_, index) => <div className="panel skeleton-card" key={index}><span /><span /><span /></div>)}</div>}>
                <LazyDashboardCharts days={days} mode="api" snapshot={snapshot} visibleIngestion={visibleIngestion} />
              </Suspense></ChartErrorBoundary>
              <div className="dashboard-section-title operations-title"><div><span className="section-kicker">STAY IN THE LOOP</span><h2>Operational activity</h2></div><span>{isApiMode ? 'Latest recorded activity' : 'Latest synthetic workspace events'}</span></div>
              <section className="operations-grid" aria-label="Recent operations">
                <ExecutionTable executions={snapshot.executions} mode="api" search={search} />
                <article className="panel activity-panel">
                  <SectionHeading title="System activity" subtitle={isApiMode ? 'Recent API events' : 'Recent demo events'} action={<span className="panel-context">{isApiMode ? 'API DATA' : 'DEMO'}</span>} />
                  <div className="activity-list">{snapshot.activities.map((activity) => <div className="activity-item" key={activity.id}>
                    <span className={`activity-icon activity-icon-${activity.tone}`}>{activity.tone === 'success' ? <Check size={15} /> : activity.tone === 'warning' ? <ArrowDownRight size={15} /> : <Database size={15} />}</span>
                    <div className="activity-copy"><strong>{activity.title}</strong><span>{activity.detail}</span><small>{activity.time}</small></div>
                  </div>)}</div>
                  {!snapshot.activities.length && <p className="activity-empty">No activity has been recorded for this workspace.</p>}
                  <div className="activity-note"><RefreshCw size={13} /> {isApiMode ? 'Activity reflects API-recorded metadata.' : 'Illustrative events, not live notifications.'}</div>
                </article>
              </section>
              </>}
            </div>
          ) : isProcessingWorkspace ? <Suspense fallback={<div className="panel operations-loading">Loading ETL workspace…</div>}><LazyDataProcessingWorkspace key={pathname} /></Suspense> : isIngestionWorkspace ? <Suspense fallback={<div className="panel operations-loading">Loading ingestion workspace…</div>}><LazyIngestionWorkspace key={pathname} page={pathname === '/data-sources' ? 'sources' : 'imports'} /></Suspense>
            : isPipelineWorkspace ? <Suspense fallback={<div className="panel operations-loading">Loading pipeline workspace…</div>}><LazyPipelineWorkspace key={pathname} page={pathname === '/monitoring' ? 'monitoring' : 'pipelines'} search={search} /></Suspense>
              : isAnalyticsWorkspace ? <Suspense fallback={<div className="panel operations-loading">Loading analytics workspace…</div>}><LazyAnalyticsWorkspace days={days} /></Suspense>
                : pathname === '/data-quality' ? <Suspense fallback={<div className="panel operations-loading">Loading quality workspace…</div>}><LazyQualityWorkspace /></Suspense>
                  : pathname === '/data-lake' || pathname === '/data-lineage' ? <Suspense fallback={<div className="panel operations-loading">Loading data lineage…</div>}><LazyArchitectureWorkspace page={pathname === '/data-lake' ? 'lake' : 'lineage'} /></Suspense>
                    : <ModulePage key={pathname} module={currentModule} snapshot={demoSnapshot} search={search} />}
          <footer className="page-footer"><span>© ImpactFlow <span> / </span> Impact Development Foundation</span><span>Built for better data decisions <span>·</span> {pathname === '/' ? (isCsvMode ? 'Browser CSV data' : isApiMode ? 'Database-backed API data' : 'API data unavailable') : isOperationalWorkspace ? 'Database-backed workspace' : 'Module preview'}</span></footer>
        </div>
      </main>
    </div>
  )
}
