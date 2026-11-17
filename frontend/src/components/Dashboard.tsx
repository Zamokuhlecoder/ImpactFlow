import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownRight, BarChart3, Check, Database, RefreshCw, ShieldCheck, UsersRound, Workflow } from 'lucide-react'
import { Navigate, useLocation } from 'react-router-dom'
import { createDashboardSnapshot } from '../data/dashboard'
import { modules } from '../data/navigation'
import { ChartErrorBoundary } from './ChartErrorBoundary'
import { ExecutionTable } from './ExecutionTable'
import { KpiCard } from './KpiCard'
import { ModulePage } from './ModulePage'
import { SectionHeading } from './SectionHeading'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const LazyDashboardCharts = lazy(() => import('./DashboardCharts'))

export default function Dashboard() {
  const { pathname } = useLocation()
  const currentModule = modules.find((item) => item.path === pathname)
  const [snapshot, setSnapshot] = useState(() => createDashboardSnapshot())
  const [seed, setSeed] = useState(2026)
  const [days, setDays] = useState(30)
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(() => new Date())
  const [refreshMessage, setRefreshMessage] = useState('')
  const visibleIngestion = useMemo(() => snapshot.ingestionTrend.slice(-days), [days, snapshot])

  useEffect(() => {
    document.title = `ImpactFlow | ${currentModule?.label ?? 'Overview'}`
    window.scrollTo(0, 0)
  }, [pathname, currentModule?.label])

  function refreshSnapshot() {
    const nextSeed = seed + 1
    setSeed(nextSeed)
    setSnapshot(createDashboardSnapshot(nextSeed))
    setLastUpdated(new Date())
    setRefreshMessage('Synthetic dashboard snapshot refreshed.')
  }

  function closeMobileNavigation() {
    setMobileOpen(false)
    if (mobileOpen) document.getElementById('mobile-nav-trigger')?.focus()
  }

  if (!currentModule) return <Navigate replace to="/" />
  const { metrics, changes } = snapshot

  return (
    <div className={`app-shell${collapsed ? ' app-shell-collapsed' : ''}`}>
      <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onCloseMobile={closeMobileNavigation} onToggleCollapse={() => setCollapsed(!collapsed)} />
      <main className="main-column">
        <Topbar activities={snapshot.activities} onOpenMobileNav={() => setMobileOpen(true)} onSearch={setSearch} search={search} title={currentModule.label} days={days} onDaysChange={setDays} onRefresh={refreshSnapshot} showRange={pathname === '/'} mobileOpen={mobileOpen} />
        <div className="page-content">
          <div className="sr-only" role="status">{refreshMessage}</div>
          {pathname === '/' ? (
            <div className="page-enter">
              <div className="page-header">
                <div><div className="eyebrow"><span className="eyebrow-line" /> YOUR DATA, IN FOCUS</div><h1>Overview<span className="heading-period">.</span></h1><p>Monitor your organisation's data operations and programme performance.</p></div>
                <div className="page-header-meta"><span className="live-indicator"><span /> DEMO WORKSPACE</span><span>Snapshot updated {new Intl.DateTimeFormat('en-ZA', { hour: '2-digit', minute: '2-digit', hour12: false }).format(lastUpdated)}</span></div>
              </div>
              <div className="demo-notice" role="note"><span className="demo-notice-icon"><Activity size={16} /></span><p><strong>Synthetic demonstration data</strong><span> A preview only — not connected to live systems.</span></p><span className="demo-notice-end">DEVELOPMENT ENVIRONMENT</span></div>
              <section aria-label="Key performance indicators" className="kpi-grid">
                <KpiCard label="Total Records" value={metrics.totalRecords} change={changes.totalRecords} description="vs. previous period" icon={Database} index={0} />
                <KpiCard label="Active Data Sources" value={metrics.activeSources} change={changes.activeSources} description="vs. previous period" icon={Activity} index={1} />
                <KpiCard label="Successful Pipelines" value={metrics.successfulPipelines} change={changes.successfulPipelines} description="vs. previous 30 days" icon={Workflow} index={2} />
                <KpiCard label="Data Quality Score" value={metrics.qualityScore} suffix="%" change={changes.qualityScore} description="vs. previous week" icon={ShieldCheck} index={3} />
                <KpiCard label="Total Beneficiaries" value={metrics.beneficiaries} change={changes.beneficiaries} description="vs. previous period" icon={UsersRound} index={4} />
                <KpiCard label="Active Programmes" value={metrics.activeProgrammes} change={changes.activeProgrammes} description="vs. previous period" icon={BarChart3} index={5} />
              </section>
              <div className="dashboard-section-title"><div><span className="section-kicker">PERFORMANCE AT A GLANCE</span><h2>Analytics overview</h2></div><span>Selected date range applies to pipeline runs and ingestion.</span></div>
              <ChartErrorBoundary><Suspense fallback={<div className="chart-grid chart-loading" aria-busy="true" aria-label="Loading dashboard charts">{Array.from({ length: 3 }, (_, index) => <div className="panel skeleton-card" key={index}><span /><span /><span /></div>)}</div>}>
                <LazyDashboardCharts days={days} snapshot={snapshot} visibleIngestion={visibleIngestion} />
              </Suspense></ChartErrorBoundary>
              <div className="dashboard-section-title operations-title"><div><span className="section-kicker">STAY IN THE LOOP</span><h2>Operational activity</h2></div><span>Latest synthetic workspace events</span></div>
              <section className="operations-grid" aria-label="Recent operations">
                <ExecutionTable executions={snapshot.executions} search={search} />
                <article className="panel activity-panel">
                  <SectionHeading title="System activity" subtitle="Recent demo events" action={<span className="panel-context">DEMO</span>} />
                  <div className="activity-list">{snapshot.activities.map((activity) => <div className="activity-item" key={activity.id}>
                    <span className={`activity-icon activity-icon-${activity.tone}`}>{activity.tone === 'success' ? <Check size={15} /> : activity.tone === 'warning' ? <ArrowDownRight size={15} /> : <Database size={15} />}</span>
                    <div className="activity-copy"><strong>{activity.title}</strong><span>{activity.detail}</span><small>{activity.time}</small></div>
                  </div>)}</div>
                  <div className="activity-note"><RefreshCw size={13} /> Illustrative events, not live notifications</div>
                </article>
              </section>
            </div>
          ) : <ModulePage key={pathname} module={currentModule} snapshot={snapshot} search={search} />}
          <footer className="page-footer"><span>© ImpactFlow <span> / </span> Impact Development Foundation</span><span>Built for better data decisions <span>·</span> Synthetic data only</span></footer>
        </div>
      </main>
    </div>
  )
}
