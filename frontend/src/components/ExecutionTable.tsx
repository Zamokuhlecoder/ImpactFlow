import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, Workflow } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { DashboardSnapshot, PipelineStatus } from '../types/dashboard'
import { SectionHeading } from './SectionHeading'

type Execution = DashboardSnapshot['executions'][number]
type SortKey = 'name' | 'source' | 'executedAt' | 'records' | 'duration' | 'status'
const formatter = new Intl.NumberFormat('en-ZA')
const dateFormatter = new Intl.DateTimeFormat('en-ZA', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })
const formatExecutionTime = (value: string) => dateFormatter.format(new Date(value))

export function StatusBadge({ status }: { status: PipelineStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}><span />{status}</span>
}

export function ExecutionTable({ executions, search }: { executions: Execution[]; search: string }) {
  const [status, setStatus] = useState('All')
  const [sortKey, setSortKey] = useState<SortKey>('executedAt')
  const [ascending, setAscending] = useState(false)
  const [page, setPage] = useState(0)
  const [showAll, setShowAll] = useState(false)

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return executions.filter((run) =>
      (status === 'All' || run.status === status) &&
      (!query || `${run.name} ${run.source} ${run.status}`.toLowerCase().includes(query)),
    ).sort((a, b) => {
      if (sortKey === 'duration') {
        return (a.durationSeconds - b.durationSeconds) * (ascending ? 1 : -1)
      }
      const left = a[sortKey]
      const right = b[sortKey]
      const comparison = typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right))
      return comparison * (ascending ? 1 : -1)
    })
  }, [executions, search, sortKey, ascending, status])
  const pageSize = 5
  const lastPage = Math.max(0, Math.ceil(filtered.length / pageSize) - 1)
  const currentPage = Math.min(page, lastPage)
  const displayed = showAll ? filtered : filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize)

  function sortBy(key: SortKey) {
    if (sortKey === key) setAscending(!ascending)
    else { setSortKey(key); setAscending(true) }
    setPage(0)
  }

  function exportExecutions() {
    const rows = [
      ['Pipeline', 'Source', 'Execution time', 'Records processed', 'Duration', 'Status'],
      ...filtered.map((run) => [run.name, run.source, formatExecutionTime(run.executedAt), run.records, run.duration, run.status]),
    ]
    const csv = rows.map((row) => row.map((field) => `"${String(field).replaceAll('"', '""')}"`).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'impactflow-demo-pipeline-executions.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const columns: Array<{ key: SortKey; label: string }> = [
    { key: 'name', label: 'Pipeline name' }, { key: 'source', label: 'Source' },
    { key: 'executedAt', label: 'Execution time' }, { key: 'records', label: 'Records' },
    { key: 'duration', label: 'Duration' }, { key: 'status', label: 'Status' },
  ]

  return (
    <article className="panel executions-panel">
      <SectionHeading title="Recent pipeline executions" subtitle="A closer look at your synthetic pipeline activity" action={
        <div className="table-actions">
          <label className="status-filter"><span className="sr-only">Filter by status</span><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(0) }}><option>All</option><option>Succeeded</option><option>Running</option><option>Failed</option></select></label>
          <button className="button button-small" onClick={exportExecutions}><Download size={14} /> Export</button>
        </div>
      } />
      <div className="table-scroll">
        <table className="execution-table">
          <thead><tr>{columns.map((column) => <th key={column.key} scope="col" aria-sort={sortKey === column.key ? (ascending ? 'ascending' : 'descending') : undefined}><button onClick={() => sortBy(column.key)}>{column.label}{sortKey === column.key && (ascending ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}</button></th>)}</tr></thead>
          <tbody>{displayed.length ? displayed.map((run) => <tr key={run.id}>
            <td><span className="pipeline-name-cell"><span className="pipeline-row-icon"><Workflow size={14} /></span>{run.name}</span></td>
            <td>{run.source}</td><td>{formatExecutionTime(run.executedAt)}</td><td>{formatter.format(run.records)}</td><td>{run.duration}</td><td><StatusBadge status={run.status} /></td>
          </tr>) : <tr><td className="empty-table" colSpan={6}>No executions match your search and filters.</td></tr>}</tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>{filtered.length ? `${showAll ? 1 : currentPage * pageSize + 1}–${showAll ? filtered.length : Math.min((currentPage + 1) * pageSize, filtered.length)} of ${filtered.length} executions` : '0 executions'}</span>
        <div>
          {filtered.length > pageSize && <button className="table-footer-link" onClick={() => { setShowAll(!showAll); setPage(0) }}>{showAll ? 'Show paginated' : 'View all executions'}</button>}
          {!showAll && <><button className="pagination-button" aria-label="Previous page" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={15} /></button><span> {currentPage + 1} / {lastPage + 1} </span><button className="pagination-button" aria-label="Next page" disabled={currentPage === lastPage} onClick={() => setPage(currentPage + 1)}><ChevronRight size={15} /></button></>}
        </div>
      </div>
    </article>
  )
}
