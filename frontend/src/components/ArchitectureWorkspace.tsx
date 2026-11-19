import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Database, GitBranch, Layers3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getProcessingDatasets } from '../services/processing'
import { RunStatusBadge } from './RunStatusBadge'

type Props = { page: 'lake' | 'lineage' }

const numberFormatter = new Intl.NumberFormat('en-ZA')

export function ArchitectureWorkspace({ page }: Props) {
  const [selectedImport, setSelectedImport] = useState('')
  const datasets = useQuery({
    queryKey: ['processing-datasets'],
    queryFn: getProcessingDatasets,
    retry: false,
  })
  const selected = useMemo(
    () => datasets.data?.find(dataset => dataset.import_id === selectedImport)
      ?? datasets.data?.[0],
    [datasets.data, selectedImport],
  )
  const run = selected?.latest_run
  const loadingError = datasets.error
  const nodes = [
    { name: 'Data sources', detail: selected?.source_name ?? 'Configured connectors', kind: 'source' },
    { name: 'Data ingestion', detail: selected ? `Import ${selected.import_id.slice(0, 8)}` : 'File and connector intake', kind: 'ingestion' },
    { name: 'Bronze', detail: selected ? `${numberFormatter.format(selected.records_received)} raw rows` : 'Original data', kind: 'bronze' },
    { name: 'Silver', detail: run ? `${numberFormatter.format(run.records_processed)} validated rows` : 'Run a pipeline to populate', kind: 'silver' },
    { name: 'Gold', detail: run && run.records_processed ? '3 analytics summary datasets' : 'Waiting for validated data', kind: 'gold' },
    { name: 'Data warehouse', detail: 'Planned · not connected', kind: 'planned' },
    { name: 'Power BI / analytics', detail: 'Planned · not connected', kind: 'planned' },
  ]

  return <div className="page-enter operations-workspace architecture-workspace">
    <div className="page-header">
      <div>
        <div className="eyebrow"><span className="eyebrow-line" /> DATA MANAGEMENT / {page === 'lake' ? 'MEDALLION STORAGE' : 'LINEAGE'}</div>
        <h1>{page === 'lake' ? 'Data Lake' : 'Data Lineage'}<span className="heading-period">.</span></h1>
        <p>{page === 'lake'
          ? 'Inspect how imported records move through the Bronze, Silver, and Gold layers.'
          : 'Trace the implemented path from a source import through validated outputs.'}</p>
      </div>
      <span className="preview-pill"><GitBranch size={14} /> IMPLEMENTED + PLANNED</span>
    </div>
    <div className="architecture-toolbar">
      <div><span className="section-kicker">DATASET CONTEXT</span><strong>{selected?.dataset_name ?? (datasets.isLoading ? 'Loading imports…' : 'No imported datasets')}</strong></div>
      <label>Imported dataset
        <select
          disabled={!datasets.data?.length}
          onChange={event => setSelectedImport(event.target.value)}
          value={selected?.import_id ?? ''}
        >
          {datasets.data?.map(dataset => <option key={dataset.import_id} value={dataset.import_id}>
            {dataset.dataset_name} · {dataset.schema_type}
          </option>)}
          {!datasets.data?.length && <option value="">No Bronze imports available</option>}
        </select>
      </label>
      {run && <RunStatusBadge status={run.status} />}
    </div>
    {loadingError && <div className="ingestion-message" role="alert">Dataset lineage could not be loaded from the API.</div>}
    <div className="architecture-flow-wrap">
      <section aria-label="ImpactFlow data architecture" className={`architecture-flow${page === 'lineage' ? ' architecture-flow-lineage' : ''}`}>
        {nodes.map((node, index) => <div className={`architecture-node architecture-node-${node.kind}`} key={node.name}>
          <span className="architecture-node-step">{String(index + 1).padStart(2, '0')}</span>
          <span aria-hidden="true" className="architecture-node-icon">
            {index < 2 ? <Database size={16} /> : index < 5 ? <Layers3 size={16} /> : <GitBranch size={16} />}
          </span>
          <div><strong>{node.name}</strong><span>{node.detail}</span></div>
          {index < nodes.length - 1 && <ArrowRight aria-hidden="true" className="architecture-connector" size={16} />}
        </div>)}
      </section>
    </div>
    <section className="panel architecture-run">
      <div className="pipeline-toolbar">
        <div><span className="section-kicker">LATEST TRANSFORMATION</span><h2>{run ? selected?.dataset_name : 'No transformation has been run'}</h2></div>
        {selected && <Link className="table-action-link" to={`/monitoring${run ? `?run=${run.id}` : ''}`}>View execution details <ArrowRight size={13} /></Link>}
      </div>
      {run ? <div className="architecture-run-metrics">
        <div><span>Pipeline</span><strong>{run.pipeline_name}</strong></div>
        <div><span>Started</span><strong>{new Date(run.started_at).toLocaleString('en-ZA')}</strong></div>
        <div><span>Received</span><strong>{numberFormatter.format(run.records_received)}</strong></div>
        <div><span>Validated</span><strong>{numberFormatter.format(run.records_processed)}</strong></div>
        <div><span>Rejected</span><strong>{numberFormatter.format(run.records_rejected)}</strong></div>
        <div><span>Quality</span><strong>{run.quality_score}%</strong></div>
      </div> : <p className="processing-empty">Bronze import details are live. Silver and Gold outputs appear after a run in <Link to="/data-processing">ETL Processing</Link>.</p>}
      <p className="pipeline-catalog-note">Silver, Gold, and quarantine use local development file storage. Warehouse and Power BI are future phases, not connected destinations.</p>
    </section>
  </div>
}
