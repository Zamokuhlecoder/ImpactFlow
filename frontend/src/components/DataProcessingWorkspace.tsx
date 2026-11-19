import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { BarChart3, Database, Play, ShieldCheck } from 'lucide-react'
import {
  getLayerData,
  getProcessingDatasets,
  getProcessingPipelines,
  getTransformationRuns,
  startTransformation,
  type ProcessingLayer,
  type TransformationRun,
} from '../services/processing'
import { RecordTable } from './RecordTable'

const layers: Array<{ value: ProcessingLayer; label: string }> = [
  { value: 'bronze', label: 'Bronze' },
  { value: 'silver', label: 'Silver' },
  { value: 'gold', label: 'Gold' },
  { value: 'quarantine', label: 'Rejected' },
]

function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return 'The processing request failed. Check the API connection and try again.'
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('en-ZA', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function RunHistory({
  runs,
  onInspect,
}: {
  runs: TransformationRun[]
  onInspect: (run: TransformationRun) => void
}) {
  if (!runs.length) return <p className="processing-empty">No transformations have run yet.</p>
  return <div className="processing-history">
    {runs.map(run => <article key={run.id}>
      <div>
        <strong>{run.pipeline_name}</strong>
        <span>{formatTime(run.started_at)} · {run.records_received.toLocaleString()} received</span>
        {run.error_details && <small className="ingestion-error">{run.error_details}</small>}
      </div>
      <div>
        <span className={`processing-status processing-status-${run.status}`}>{run.status}</span>
        <span>{run.records_processed.toLocaleString()} valid · {run.records_rejected.toLocaleString()} rejected · {run.quality_score}% quality</span>
        <button className="button button-small" onClick={() => onInspect(run)} type="button">Inspect layers</button>
      </div>
    </article>)}
  </div>
}

export function DataProcessingWorkspace() {
  const queryClient = useQueryClient()
  const [selectedImportId, setSelectedImportId] = useState('')
  const [selectedPipeline, setSelectedPipeline] = useState('standardize_validate')
  const [selectedLayer, setSelectedLayer] = useState<ProcessingLayer>('bronze')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const pipelines = useQuery({
    queryKey: ['processing-pipelines'],
    queryFn: getProcessingPipelines,
    retry: false,
  })
  const datasets = useQuery({
    queryKey: ['processing-datasets'],
    queryFn: getProcessingDatasets,
    retry: false,
  })
  const runs = useQuery({
    queryKey: ['processing-runs'],
    queryFn: getTransformationRuns,
    retry: false,
  })
  const importId = selectedImportId || datasets.data?.[0]?.import_id || ''
  const selectedDataset = datasets.data?.find(dataset => dataset.import_id === importId)
  const layerData = useQuery({
    queryKey: ['processing-layer', importId, selectedLayer],
    queryFn: () => getLayerData(importId, selectedLayer),
    enabled: Boolean(importId),
    retry: false,
  })
  const workspaceError = pipelines.error ?? datasets.error ?? runs.error
  const layerError = layerData.error
  const report = selectedDataset?.latest_run?.quality_report

  async function processDataset() {
    if (!importId) return
    setBusy(true)
    setNotice('')
    try {
      const result = await startTransformation(importId, selectedPipeline)
      setNotice(result.status === 'failed'
        ? `Transformation failed: ${result.error_details ?? 'No error details were returned.'}`
        : `Transformation ${result.status}: ${result.records_processed.toLocaleString()} valid, ${result.records_rejected.toLocaleString()} rejected.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['processing-datasets'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-runs'] }),
        queryClient.invalidateQueries({ queryKey: ['processing-layer'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-snapshot'] }),
      ])
    } catch (error) {
      setNotice(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  function inspectRun(run: TransformationRun) {
    setSelectedImportId(run.dataset_import_id)
    setSelectedLayer('silver')
  }

  return <div className="page-enter ingestion-workspace processing-workspace">
    <div className="page-header">
      <div>
        <div className="eyebrow"><span className="eyebrow-line" /> DATA MANAGEMENT / TRANSFORMATIONS</div>
        <h1>ETL Processing<span className="heading-period">.</span></h1>
        <p>Transform preserved Bronze data into validated Silver records and Gold summaries.</p>
      </div>
      <span className="preview-pill"><Database size={14} /> DATABASE-BACKED</span>
    </div>
    <div className="demo-notice">
      <span className="demo-notice-icon"><ShieldCheck size={16} /></span>
      <p><strong>Local development data only.</strong><span> Transformations use the API database and local layer storage. Upload synthetic data only; the API does not enforce authentication.</span></p>
    </div>
    {notice && <div className="ingestion-message" role="status">{notice}</div>}
    {workspaceError && <div className="ingestion-message" role="alert">{errorMessage(workspaceError)}</div>}
    <div className="processing-grid">
      <section className="panel ingestion-panel">
        <div className="section-kicker">TRANSFORMATION JOB</div>
        <h2>Select a Bronze dataset</h2>
        <div className="ingestion-form">
          <label>Available dataset
            <select
              onChange={event => setSelectedImportId(event.target.value)}
              value={importId}
            >
              <option value="" disabled>Select an imported dataset</option>
              {datasets.data?.map(dataset => <option key={dataset.import_id} value={dataset.import_id}>
                {dataset.dataset_name} · {dataset.schema_type} · {dataset.records_received.toLocaleString()} rows
              </option>)}
            </select>
          </label>
          <label>Processing pipeline
            <select
              onChange={event => setSelectedPipeline(event.target.value)}
              value={selectedPipeline}
            >
              {pipelines.data?.map(pipeline => <option key={pipeline.name} value={pipeline.name}>{pipeline.label}</option>)}
            </select>
          </label>
          {selectedDataset && <p>Source: {selectedDataset.source_name}. Imported {formatTime(selectedDataset.imported_at)}. Original file remains unchanged in Bronze.</p>}
          <button
            className="button button-primary"
            disabled={busy || !importId || !pipelines.data?.length}
            onClick={() => { void processDataset() }}
            type="button"
          >
            <Play size={14} /> {busy ? 'Processing…' : 'Run transformation'}
          </button>
          {!datasets.isLoading && !datasets.data?.length && <p>No Bronze datasets are available. Upload a dataset in Data Ingestion first.</p>}
        </div>
      </section>
      <section className="panel ingestion-panel">
        <div className="section-kicker">LATEST DATA QUALITY</div>
        <h2>{selectedDataset?.dataset_name ?? 'Select a dataset'}</h2>
        {report ? <>
          <div className="processing-quality-score"><strong>{report.quality_percentage}%</strong><span>valid Silver records</span></div>
          <div className="processing-quality-grid">
            <div><span>Total</span><strong>{report.total_records.toLocaleString()}</strong></div>
            <div><span>Valid</span><strong>{report.valid_records.toLocaleString()}</strong></div>
            <div><span>Invalid</span><strong>{report.invalid_records.toLocaleString()}</strong></div>
            <div><span>Duplicates</span><strong>{report.duplicate_records.toLocaleString()}</strong></div>
            <div><span>Missing values</span><strong>{report.missing_values.toLocaleString()}</strong></div>
          </div>
        </> : <p className="processing-empty">Run a pipeline to create a data quality report.</p>}
      </section>
    </div>
    <section className="panel ingestion-panel processing-layers">
      <div className="section-kicker">MEDALLION DATA</div>
      <h2>{selectedDataset?.dataset_name ?? 'Dataset layers'}</h2>
      <div aria-label="Data layer" className="processing-layer-tabs" role="group">
        {layers.map(layer => <button
          aria-pressed={selectedLayer === layer.value}
          className="button button-small"
          key={layer.value}
          onClick={() => setSelectedLayer(layer.value)}
          type="button"
        >{layer.label}</button>)}
      </div>
      {layerError && <div className="ingestion-message" role="alert">{errorMessage(layerError)}</div>}
      {layerData.isLoading ? <p className="processing-empty">Loading layer records…</p> : layerData.data?.datasets.length ? (
        <div className="processing-layer-datasets">{layerData.data.datasets.map(dataset => <section key={dataset.name}>
          <h3>{dataset.name}</h3>
          <RecordTable records={dataset.records} />
        </section>)}</div>
      ) : <p className="processing-empty">{selectedLayer === 'bronze' ? 'No original rows are available.' : 'Run a successful transformation to populate this layer.'}</p>}
      {selectedLayer === 'gold' && <p className="processing-table-note"><BarChart3 size={13} /> Gold outputs include programme performance, provincial performance, and aggregate beneficiary summary datasets.</p>}
    </section>
    <section className="panel ingestion-panel ingestion-history">
      <div className="section-kicker">TRANSFORMATION HISTORY</div>
      <h2>Recent processing runs</h2>
      {runs.isLoading ? <p className="processing-empty">Loading transformation history…</p> : runs.data && <RunHistory runs={runs.data} onInspect={inspectRun} />}
    </section>
  </div>
}
