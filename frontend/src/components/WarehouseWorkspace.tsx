import { useQuery } from '@tanstack/react-query'
import { Database, Layers3, RefreshCw, ShieldCheck } from 'lucide-react'
import { getWarehouseLoads, getWarehouseOverview } from '../services/warehouse'

const numberFormatter = new Intl.NumberFormat('en-ZA')

export function WarehouseWorkspace() {
  const overview = useQuery({ queryKey: ['warehouse-overview'], queryFn: getWarehouseOverview, retry: false })
  const loads = useQuery({ queryKey: ['warehouse-loads'], queryFn: getWarehouseLoads, retry: false })
  const data = overview.data

  return <div className="page-enter operations-workspace">
    <div className="page-header">
      <div><div className="eyebrow"><span className="eyebrow-line" /> PLATFORM / WAREHOUSE</div><h1>Data Warehouse<span className="heading-period">.</span></h1><p>PostgreSQL analytical star schema loaded from validated Silver records.</p></div>
      <span className="preview-pill">{overview.isSuccess ? 'LIVE WAREHOUSE' : 'DATABASE WAREHOUSE'}</span>
    </div>
    {overview.isError && <div className="ingestion-message" role="alert">Warehouse metadata could not be loaded from the database API.</div>}
    {overview.isLoading && <div className="panel operations-loading" aria-busy="true">Loading warehouse metadata…</div>}
    {data && <>
      <section aria-label="Warehouse metrics" className="kpi-grid analytics-kpi-grid">
        <Metric label="Participation facts" value={data.facts.participation ?? 0} icon={Database} />
        <Metric label="Programme outcomes" value={data.facts.programme_outcomes ?? 0} icon={Layers3} />
        <Metric label="Beneficiary dimensions" value={data.dimensions.beneficiaries ?? 0} icon={ShieldCheck} />
        <Metric label="Latest load" value={data.latest_load?.status ?? 'not loaded'} icon={RefreshCw} />
      </section>
      <div className="module-grid">
        <article className="panel module-main">
          <div className="dashboard-section-title"><div><span className="section-kicker">WAREHOUSE CATALOGUE</span><h2>Dimensions and facts</h2></div><span>Counts are database-backed.</span></div>
          <div className="schema-preview"><div><span className="section-kicker">DIMENSIONS</span>{Object.entries(data.dimensions).map(([name, count]) => <span className="schema-chip" key={name}>{name} · {numberFormatter.format(count)}</span>)}</div><div><span className="section-kicker">FACTS</span>{Object.entries(data.facts).map(([name, count]) => <span className="schema-chip fact-chip" key={name}>{name} · {numberFormatter.format(count)}</span>)}</div></div>
          <div className="dashboard-section-title"><div><span className="section-kicker">FIELD COVERAGE</span><h2>Supported source fields</h2></div></div>
          <div className="capability-list">{data.supported_fields.map((field) => <div key={field}><span className="capability-number">✓</span><div><strong>{field}</strong><span>Available from current Silver schemas</span></div><span className="sample-tag">SUPPORTED</span></div>)}</div>
          <div className="demo-notice"><p><strong>Not yet available</strong><span> {data.unavailable_fields.join(', ')}. These are not inferred or fabricated.</span></p></div>
        </article>
        <article className="panel module-side">
          <div className="dashboard-section-title"><div><span className="section-kicker">LOAD HISTORY</span><h2>Silver to warehouse</h2></div></div>
          {loads.data?.map((load) => <div className="feature-list" key={load.id}><div><span>{load.status.toUpperCase()}</span><strong>{numberFormatter.format(load.records_loaded)} loaded / {numberFormatter.format(load.records_skipped)} skipped</strong></div></div>)}
          {!loads.isLoading && !loads.data?.length && <div className="module-empty"><strong>No warehouse loads yet</strong><p>Run a successful ETL transformation to populate the warehouse.</p></div>}
        </article>
      </div>
    </>}
  </div>
}

function Metric({ label, value, icon: Icon }: { label: string; value: number | string; icon: typeof Database }) {
  return <article className="kpi-card"><div className="kpi-card-top"><span className="kpi-label">{label}</span><Icon size={17} /></div><strong className="kpi-value">{typeof value === 'number' ? numberFormatter.format(value) : value}</strong><span className="kpi-description">warehouse API</span></article>
}
