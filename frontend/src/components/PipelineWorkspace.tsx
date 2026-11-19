import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Clock3, ExternalLink, Search, Workflow } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { getProcessingDatasets, getProcessingPipelines, getTransformationRuns } from '../services/processing'
import type { TransformationRun } from '../services/processing'
import { RunStatusBadge } from './RunStatusBadge'

type Props = { page: 'pipelines' | 'monitoring'; search: string }
type StageStatus = 'complete' | 'warning' | 'failed' | 'not-recorded'

const numberFormatter = new Intl.NumberFormat('en-ZA')
const dateFormatter = new Intl.DateTimeFormat('en-ZA', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function duration(run: TransformationRun): number | null {
  if (!run.completed_at) return null
  return Math.max(0, (Date.parse(run.completed_at) - Date.parse(run.started_at)) / 1000)
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return 'In progress'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function throughput(run: TransformationRun): string {
  const seconds = duration(run)
  if (seconds === null || seconds === 0) return '—'
  return `${numberFormatter.format(Math.round(run.records_processed / seconds))} records/s`
}

function mostRecentSuccessful(runs: TransformationRun[]): TransformationRun | undefined {
  return runs.find(run => run.status === 'succeeded')
}

function ExecutionFlow({ run }: { run: TransformationRun }) {
  const isFailed = run.status === 'failed'
  const hasRejects = run.records_rejected > 0
  const stages: Array<{ name: string; detail: string; status: StageStatus }> = [
    {
      name: 'Extract',
      detail: isFailed ? 'Stage outcome unavailable' : `${numberFormatter.format(run.records_received)} received`,
      status: isFailed ? 'not-recorded' : 'complete',
    },
    {
      name: 'Validate',
      detail: isFailed ? 'Stage outcome unavailable' : `${numberFormatter.format(run.records_rejected)} rejected`,
      status: isFailed ? 'not-recorded' : hasRejects ? 'warning' : 'complete',
    },
    {
      name: 'Transform',
      detail: isFailed ? 'Stage outcome unavailable' : `${numberFormatter.format(run.records_processed)} valid`,
      status: isFailed ? 'not-recorded' : 'complete',
    },
    {
      name: 'Load',
      detail: run.status === 'failed' ? 'Output not confirmed' : 'Layer files written',
      status: isFailed ? 'not-recorded' : 'complete',
    },
  ]
  return <div aria-label="Extract, validate, transform and load stages" className="execution-flow">
    {stages.map((stage, index) => <div className={`execution-stage execution-stage-${stage.status}`} key={stage.name}>
      <span className="execution-stage-index">0{index + 1}</span>
      <strong>{stage.name}</strong>
      <span>{stage.detail}</span>
      <small>{stage.status === 'not-recorded' ? 'Stage not recorded' : stage.status}</small>
      {index < stages.length - 1 && <ArrowRight aria-hidden="true" className="execution-stage-arrow" size={15} />}
    </div>)}
  </div>
}

function PipelineCatalog({ search, runs }: { search: string; runs: TransformationRun[] }) {
  const pipelines = useQuery({
    queryKey: ['processing-pipelines'],
    queryFn: getProcessingPipelines,
    retry: false,
  })
  const datasetsQuery = useQuery({
    queryKey: ['processing-datasets'],
    queryFn: getProcessingDatasets,
    retry: false,
  })
  const [localSearch, setLocalSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const latest = runs[0]
  const lastSuccess = mostRecentSuccessful(runs)
  const failedRuns = runs.filter(run => run.status === 'failed').length
  const records = runs.reduce((total, run) => total + run.records_received, 0)
  const combinedSearch = `${search} ${localSearch}`.trim().toLowerCase()
  const filtered = useMemo(() => {
    return (pipelines.data ?? []).filter(pipeline => {
      const state = latest?.status ?? 'not run'
      const datasetName = datasetsQuery.data?.find(
        dataset => dataset.import_id === latest?.dataset_import_id,
      )?.dataset_name ?? ''
      return (statusFilter === 'all' || state === statusFilter)
        && (!combinedSearch || `${pipeline.label} ${pipeline.description} ${latest?.schema_type ?? ''} ${datasetName}`.toLowerCase().includes(combinedSearch))
    })
  }, [combinedSearch, datasetsQuery.data, latest, pipelines.data, statusFilter])
  const error = pipelines.error ?? datasetsQuery.error

  return <div className="page-enter operations-workspace">
    {error && <div className="ingestion-message" role="alert">Pipeline metadata could not be loaded from the API.</div>}
    <section aria-label="Pipeline execution summary" className="operations-metrics">
      <article><span>Pipeline definitions</span><strong>{pipelines.data?.length ?? '—'}</strong><small>Available from processing API</small></article>
      <article><span>Total executions</span><strong>{numberFormatter.format(runs.length)}</strong><small>Recorded transformation runs</small></article>
      <article><span>Records received</span><strong>{numberFormatter.format(records)}</strong><small>Across listed executions</small></article>
      <article><span>Failed executions</span><strong>{numberFormatter.format(failedRuns)}</strong><small>Requires investigation</small></article>
    </section>
    <section className="panel pipeline-catalog">
      <div className="pipeline-toolbar">
        <div><span className="section-kicker">PIPELINE CATALOG</span><h2>Registered pipelines</h2></div>
        <div className="pipeline-controls">
          <label className="pipeline-search"><Search size={15} /><span className="sr-only">Filter pipelines</span><input onChange={event => setLocalSearch(event.target.value)} placeholder="Filter pipelines" value={localSearch} /></label>
          <label className="status-filter"><span className="sr-only">Filter pipeline status</span><select onChange={event => setStatusFilter(event.target.value)} value={statusFilter}>
            <option value="all">All statuses</option><option value="succeeded">Succeeded</option><option value="warning">Warning</option><option value="failed">Failed</option><option value="running">Running</option><option value="not run">Not run</option>
          </select></label>
        </div>
      </div>
      <div className="table-scroll">
        <table className="execution-table pipeline-table">
          <thead><tr><th scope="col">Pipeline</th><th scope="col">Status</th><th scope="col">Owner</th><th scope="col">Last successful run</th><th scope="col">Duration</th><th scope="col">Records</th><th scope="col">Failures</th><th scope="col">Actions</th></tr></thead>
          <tbody>{filtered.map(pipeline => {
            const run = runs[0]
            const lastDataset = datasetsQuery.data?.find(
              dataset => dataset.import_id === run?.dataset_import_id,
            )
            return <tr key={pipeline.name}>
              <td><span className="pipeline-name-cell"><span className="pipeline-row-icon"><Workflow size={14} /></span><span><strong>{pipeline.label}</strong><small>{pipeline.name}{lastDataset ? ` · ${lastDataset.dataset_name}` : ''}</small></span></span></td>
              <td>{run ? <RunStatusBadge status={run.status} /> : <RunStatusBadge status="Not run" />}</td>
              <td>Unassigned</td>
              <td>{lastSuccess ? dateFormatter.format(new Date(lastSuccess.completed_at ?? lastSuccess.started_at)) : 'No successful run'}</td>
              <td>{formatDuration(run ? duration(run) : null)}</td>
              <td>{numberFormatter.format(run?.records_received ?? 0)}</td>
              <td>{numberFormatter.format(failedRuns)}</td>
              <td><span className="pipeline-row-actions">
                {run && <Link className="table-action-link" to={`/monitoring?run=${run.id}`}>View</Link>}
                <Link className="table-action-link" to="/data-processing">Run</Link>
              </span></td>
            </tr>
          })}{!filtered.length && <tr><td className="empty-table" colSpan={8}>{pipelines.isLoading ? 'Loading pipeline catalog…' : 'No pipelines match these filters.'}</td></tr>}</tbody>
        </table>
      </div>
      <p className="pipeline-catalog-note">Pipeline definitions are code-managed; ownership is not tracked by the current API. Execution remains available in the ETL Processing workspace.</p>
    </section>
    <section className="panel pipeline-history">
      <div className="pipeline-toolbar"><div><span className="section-kicker">EXECUTION HISTORY</span><h2>Recent runs</h2></div><Link className="table-action-link" to="/monitoring">Open monitoring <ExternalLink size={13} /></Link></div>
      <RunHistoryTable datasets={datasetsQuery.data ?? []} runs={runs} />
    </section>
  </div>
}

function RunHistoryTable({
  runs,
  datasets,
}: {
  runs: TransformationRun[]
  datasets: Array<{ import_id: string; dataset_name: string }>
}) {
  if (!runs.length) return <p className="processing-empty">No transformation runs have been recorded.</p>
  return <div className="table-scroll">
    <table className="execution-table pipeline-table">
      <thead><tr><th scope="col">Started</th><th scope="col">Dataset</th><th scope="col">Status</th><th scope="col">Duration</th><th scope="col">Received</th><th scope="col">Processed</th><th scope="col">Rejected</th><th scope="col">Quality</th></tr></thead>
      <tbody>{runs.slice(0, 10).map(run => <tr key={run.id}>
        <td>{dateFormatter.format(new Date(run.started_at))}</td>
        <td>{datasets.find(dataset => dataset.import_id === run.dataset_import_id)?.dataset_name ?? run.dataset_import_id.slice(0, 8)}</td>
        <td><RunStatusBadge status={run.status} /></td>
        <td>{formatDuration(duration(run))}</td>
        <td>{numberFormatter.format(run.records_received)}</td>
        <td>{numberFormatter.format(run.records_processed)}</td>
        <td>{numberFormatter.format(run.records_rejected)}</td>
        <td>{run.quality_score}%</td>
      </tr>)}</tbody>
    </table>
  </div>
}

function ExecutionMonitor({
  runs,
  datasets,
  selectedRunId,
  onSelect,
}: {
  runs: TransformationRun[]
  datasets: Awaited<ReturnType<typeof getProcessingDatasets>>
  selectedRunId: string
  onSelect: (id: string) => void
}) {
  const selectedRun = runs.find(run => run.id === selectedRunId) ?? runs[0]
  const dataset = datasets.find(item => item.import_id === selectedRun?.dataset_import_id)
  if (!selectedRun) return <div className="panel pipeline-empty">
    <span className="section-kicker">EXECUTION MONITOR</span>
    <h2>No transformation runs yet</h2>
    <p>Start a transformation to see its status, record counts, and layer outputs here.</p>
    <Link className="button button-primary" to="/data-processing">Open processing workspace</Link>
  </div>
  const seconds = duration(selectedRun)
  return <>
    <section className="panel monitor-run-header">
      <div><span className="section-kicker">SELECTED EXECUTION</span><h2>{dataset?.dataset_name ?? selectedRun.pipeline_name}</h2><p>{selectedRun.pipeline_name} · {selectedRun.schema_type} · run {selectedRun.id.slice(0, 8)}</p></div>
      <label className="monitor-run-select"><span>Execution</span><select onChange={event => onSelect(event.target.value)} value={selectedRun.id}>
        {runs.map(run => <option key={run.id} value={run.id}>{dateFormatter.format(new Date(run.started_at))} · {run.status} · {run.id.slice(0, 8)}</option>)}
      </select></label>
      <RunStatusBadge status={selectedRun.status} />
    </section>
    <section aria-label="Selected execution metrics" className="monitor-metrics">
      <article><span>Started</span><strong>{dateFormatter.format(new Date(selectedRun.started_at))}</strong></article>
      <article><span>Completed</span><strong>{selectedRun.completed_at ? dateFormatter.format(new Date(selectedRun.completed_at)) : 'In progress'}</strong></article>
      <article><span>Total duration</span><strong>{formatDuration(seconds)}</strong></article>
      <article><span>Throughput</span><strong>{throughput(selectedRun)}</strong></article>
      <article><span>Received</span><strong>{numberFormatter.format(selectedRun.records_received)}</strong></article>
      <article><span>Processed</span><strong>{numberFormatter.format(selectedRun.records_processed)}</strong></article>
      <article><span>Rejected</span><strong>{numberFormatter.format(selectedRun.records_rejected)}</strong></article>
      <article><span>Quality</span><strong>{selectedRun.quality_score}%</strong></article>
    </section>
    <section className="panel monitor-section">
      <div className="pipeline-toolbar"><div><span className="section-kicker">EXECUTION FLOW</span><h2>Extract / validate / transform / load</h2></div><span className="pipeline-catalog-note">Per-stage timings are not recorded by this pipeline.</span></div>
      <ExecutionFlow run={selectedRun} />
    </section>
    <section className="panel monitor-section">
      <div className="pipeline-toolbar"><div><span className="section-kicker">EXECUTION LOG</span><h2>Run diagnostics</h2></div><Clock3 size={15} aria-hidden="true" /></div>
      {selectedRun.error_details ? <p className="monitor-error" role="alert">{selectedRun.error_details}</p> : <p className="processing-empty">No error was recorded. Step-level logs are not captured by the current runner.</p>}
      <div className="monitor-log-meta"><span>Run ID <strong>{selectedRun.id}</strong></span><span>Import <strong>{selectedRun.dataset_import_id}</strong></span></div>
    </section>
  </>
}

export function PipelineWorkspace({ page, search }: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const runs = useQuery({
    queryKey: ['processing-runs'],
    queryFn: getTransformationRuns,
    retry: false,
  })
  const datasets = useQuery({
    queryKey: ['processing-datasets'],
    queryFn: getProcessingDatasets,
    retry: false,
  })
  const currentRun = searchParams.get('run') ?? ''
  function selectRun(id: string) {
    setSearchParams(id ? { run: id } : {})
  }
  const pageError = runs.error ?? (page === 'monitoring' ? datasets.error : null)

  return <div className="page-enter operations-workspace">
    {page === 'pipelines' ? <>
      <div className="page-header">
        <div><div className="eyebrow"><span className="eyebrow-line" /> DATA MANAGEMENT / EXECUTION</div><h1>Data Pipelines<span className="heading-period">.</span></h1><p>Manage the registered transformation pipeline and review its real execution history.</p></div>
        <Link className="button button-primary" to="/data-processing">Open processing workspace <ArrowRight size={14} /></Link>
      </div>
      {runs.isLoading ? <div className="panel operations-loading">Loading pipeline activity…</div> : pageError
        ? <div className="ingestion-message" role="alert">Pipeline activity could not be loaded from the API.</div>
        : <PipelineCatalog search={search} runs={runs.data ?? []} />}
    </> : <>
      <div className="page-header">
        <div><div className="eyebrow"><span className="eyebrow-line" /> OPERATIONS / OBSERVABILITY</div><h1>Pipeline Monitoring<span className="heading-period">.</span></h1><p>Inspect recorded ETL executions, throughput, validation outcomes, and available diagnostics.</p></div>
        <Link className="button" to="/data-pipelines">Pipeline catalog <ArrowRight size={14} /></Link>
      </div>
      {pageError && <div className="ingestion-message" role="alert">Execution details could not be loaded from the API.</div>}
      {runs.isLoading || datasets.isLoading ? <div className="panel operations-loading">Loading execution details…</div> : <ExecutionMonitor
        datasets={datasets.data ?? []}
        onSelect={selectRun}
        runs={runs.data ?? []}
        selectedRunId={currentRun}
      />}
    </>}
  </div>
}
