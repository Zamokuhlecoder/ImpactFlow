import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getLayerData, getProcessingDatasets, getTransformationRuns, type ProcessingLayer } from '../services/processing'
import { RecordTable } from './RecordTable'
import { RunStatusBadge } from './RunStatusBadge'

const numberFormatter = new Intl.NumberFormat('en-ZA')

export function QualityWorkspace() {
  const [selectedImport, setSelectedImport] = useState('')
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
  const selected = useMemo(
    () => datasets.data?.find(dataset => dataset.import_id === selectedImport)
      ?? datasets.data?.find(dataset => dataset.latest_run?.records_rejected)
      ?? datasets.data?.[0],
    [datasets.data, selectedImport],
  )
  const selectedRun = selected?.latest_run
  const quarantine = useQuery({
    queryKey: ['processing-layer', selected?.import_id, 'quarantine' satisfies ProcessingLayer],
    queryFn: () => getLayerData(selected?.import_id ?? '', 'quarantine'),
    enabled: Boolean(selectedRun && selected?.import_id),
    retry: false,
  })
  const allRuns = runs.data ?? []
  const totalRecords = allRuns.reduce((sum, run) => sum + run.records_received, 0)
  const validRecords = allRuns.reduce((sum, run) => sum + run.records_processed, 0)
  const rejectedRecords = allRuns.reduce((sum, run) => sum + run.records_rejected, 0)
  const duplicateRecords = allRuns.reduce((sum, run) => sum + run.duplicate_records, 0)
  const missingValues = allRuns.reduce((sum, run) => sum + run.missing_values, 0)
  const score = totalRecords ? Math.round(validRecords / totalRecords * 1000) / 10 : null
  const error = datasets.error ?? runs.error ?? quarantine.error
  const rejectedRows = quarantine.data?.datasets.flatMap(dataset => dataset.records) ?? []

  return <div className="page-enter operations-workspace">
    <div className="page-header">
      <div><div className="eyebrow"><span className="eyebrow-line" /> INTELLIGENCE / VALIDATION</div><h1>Data Quality<span className="heading-period">.</span></h1><p>Review outcomes recorded by the ETL pipeline and inspect quarantined rows.</p></div>
      <Link className="button button-primary" to="/data-processing">Open ETL Processing</Link>
    </div>
    {error && <div className="ingestion-message" role="alert">Quality results could not be loaded from the API.</div>}
    <section aria-label="Data quality totals" className="operations-metrics quality-metrics">
      <article><span>Quality rate</span><strong>{score === null ? '—' : `${score}%`}</strong><small>Valid rows / received rows across listed runs</small></article>
      <article><span>Rows received</span><strong>{numberFormatter.format(totalRecords)}</strong><small>Transformation run totals</small></article>
      <article><span>Rows rejected</span><strong>{numberFormatter.format(rejectedRecords)}</strong><small>Invalid and duplicate rows</small></article>
      <article><span>Duplicate rows</span><strong>{numberFormatter.format(duplicateRecords)}</strong><small>Quarantined, not dropped</small></article>
      <article><span>Missing values</span><strong>{numberFormatter.format(missingValues)}</strong><small>Detected before validation</small></article>
    </section>
    <section className="panel quality-review">
      <div className="pipeline-toolbar">
        <div><span className="section-kicker">QUARANTINE REVIEW</span><h2>{selected?.dataset_name ?? 'Select a processed dataset'}</h2></div>
        <label className="monitor-run-select"><span>Dataset</span><select
          onChange={event => setSelectedImport(event.target.value)}
          value={selected?.import_id ?? ''}
        >
          {datasets.data?.map(dataset => <option key={dataset.import_id} value={dataset.import_id}>{dataset.dataset_name}</option>)}
        </select></label>
        {selectedRun && <RunStatusBadge status={selectedRun.status} />}
      </div>
      {selectedRun
        ? <RecordTable emptyMessage="No rows were rejected for this dataset." records={rejectedRows} />
        : <p className="processing-empty">Run a pipeline to populate persisted validation results and quarantine.</p>}
    </section>
    <section className="panel pipeline-history">
      <div className="pipeline-toolbar"><div><span className="section-kicker">QUALITY BY RUN</span><h2>Validation history</h2></div><span className="pipeline-catalog-note">Score is calculated from persisted run totals.</span></div>
      {!allRuns.length ? <p className="processing-empty">{runs.isLoading ? 'Loading quality history…' : 'No quality runs are recorded yet.'}</p> : <div className="table-scroll">
        <table className="execution-table pipeline-table">
          <thead><tr><th scope="col">Run</th><th scope="col">Status</th><th scope="col">Received</th><th scope="col">Valid</th><th scope="col">Invalid</th><th scope="col">Duplicates</th><th scope="col">Missing</th><th scope="col">Quality</th></tr></thead>
          <tbody>{allRuns.map(run => <tr key={run.id}>
            <td><Link className="table-action-link" to={`/monitoring?run=${run.id}`}>{run.id.slice(0, 8)}</Link></td>
            <td><RunStatusBadge status={run.status} /></td>
            <td>{numberFormatter.format(run.records_received)}</td>
            <td>{numberFormatter.format(run.quality_report.valid_records)}</td>
            <td>{numberFormatter.format(run.quality_report.invalid_records)}</td>
            <td>{numberFormatter.format(run.duplicate_records)}</td>
            <td>{numberFormatter.format(run.missing_values)}</td>
            <td>{run.quality_score}%</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </section>
  </div>
}
