import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClock, CircleAlert, Play, RefreshCw, Workflow } from 'lucide-react'
import { getOrchestrationDags, getOrchestrationRuns, getOrchestrationSummary, triggerOrchestrationDag } from '../services/orchestration'

const numberFormatter = new Intl.NumberFormat('en-ZA')
const dateFormatter = new Intl.DateTimeFormat('en-ZA', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })

export function OrchestrationWorkspace() {
  const queryClient = useQueryClient()
  const summary = useQuery({ queryKey: ['orchestration-summary'], queryFn: getOrchestrationSummary, retry: false })
  const dags = useQuery({ queryKey: ['orchestration-dags'], queryFn: getOrchestrationDags, retry: false })
  const runs = useQuery({ queryKey: ['orchestration-runs'], queryFn: getOrchestrationRuns, retry: false })
  const trigger = useMutation({
    mutationFn: (dagId: string) => triggerOrchestrationDag(dagId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['orchestration-summary'] })
      void queryClient.invalidateQueries({ queryKey: ['orchestration-runs'] })
    },
  })
  const data = summary.data
  const error = summary.error ?? dags.error ?? runs.error

  return <div className="page-enter operations-workspace">
    <div className="page-header">
      <div><div className="eyebrow"><span className="eyebrow-line" /> OPERATIONS / ORCHESTRATION</div><h1>Pipeline Orchestration<span className="heading-period">.</span></h1><p>Scheduled and repeatable workflows coordinated by Apache Airflow.</p></div>
      <span className="preview-pill">{data?.available ? 'LIVE AIRFLOW' : 'AIRFLOW UNAVAILABLE'}</span>
    </div>
    {error && <div className="ingestion-message" role="alert">Airflow orchestration is unavailable. Start the local Airflow services and configure the API connection.</div>}
    {trigger.isError && <div className="ingestion-message" role="alert">The DAG could not be triggered. No execution was recorded as successful.</div>}
    {data?.message && <div className="demo-notice"><CircleAlert size={16} /><p>{data.message}</p></div>}
    {data && <section aria-label="Orchestration metrics" className="kpi-grid analytics-kpi-grid">
      <Metric label="Total DAGs" value={data.total_dags} icon={Workflow} />
      <Metric label="Active pipelines" value={data.active_dags} icon={CalendarClock} />
      <Metric label="Running runs" value={data.running_runs} icon={RefreshCw} />
      <Metric label="Failed runs" value={data.failed_runs} icon={CircleAlert} />
    </section>}
    <div className="module-grid">
      <article className="panel module-main">
        <div className="dashboard-section-title"><div><span className="section-kicker">DAG MANAGEMENT</span><h2>Registered workflows</h2></div><span>Airflow API data</span></div>
        {dags.data?.length ? <div className="table-scroll"><table className="execution-table pipeline-table"><thead><tr><th>DAG</th><th>Schedule</th><th>Status</th><th>Action</th></tr></thead><tbody>{dags.data.map((dag) => <tr key={dag.dag_id}><td><strong>{dag.dag_id}</strong><small>{dag.description}</small></td><td>{dag.schedule ?? 'Manual'}</td><td>{dag.is_paused ? 'Paused' : 'Active'}</td><td><button className="table-action-link" disabled={trigger.isPending || dag.is_paused} onClick={() => trigger.mutate(dag.dag_id)} type="button"><Play size={13} /> Trigger</button></td></tr>)}</tbody></table></div> : <p className="processing-empty">No Airflow DAGs are available.</p>}
      </article>
      <article className="panel module-side">
        <div className="dashboard-section-title"><div><span className="section-kicker">EXECUTION HISTORY</span><h2>Recent runs</h2></div></div>
        {runs.data?.length ? <div className="feature-list">{runs.data.slice(0, 8).map((run) => <div key={run.id}><span>{run.status.toUpperCase()}</span><strong>{run.airflow_dag_id}</strong><small>{dateFormatter.format(new Date(run.execution_date))} · {run.trigger_type}</small></div>)}</div> : <p className="processing-empty">No orchestrated runs have been recorded.</p>}
      </article>
    </div>
  </div>
}

function Metric({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Workflow }) {
  return <article className="kpi-card"><div className="kpi-card-top"><span className="kpi-label">{label}</span><Icon size={17} /></div><strong className="kpi-value">{numberFormatter.format(value)}</strong><span className="kpi-description">Airflow API</span></article>
}
