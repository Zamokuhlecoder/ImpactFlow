import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Database, UploadCloud } from 'lucide-react'
import { apiClient } from '../services/api'

interface Source {
  id: string
  name: string
  source_type: string
  description: string | null
  connection_ref: string | null
  status: string
  records_count: number
  last_synced_at: string | null
  created_at: string
}

interface Connection {
  reference: string
  kind: 'rest' | 'postgresql'
}

interface ImportRecord {
  id: string
  source_name: string
  source_type: string
  dataset_name: string
  status: string
  records_received: number
  error_message: string | null
  created_at: string
}

interface Dataset {
  id: string
  name: string
  created_at: string
}

interface Props {
  page: 'sources' | 'imports'
}

function message(error: unknown): string {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return 'The request could not be completed. Check your connection and try again.'
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never'
}

export function IngestionWorkspace({ page }: Props) {
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [sourceType, setSourceType] = useState('CSV')
  const [editing, setEditing] = useState<string | null>(null)
  const sources = useQuery({
    queryKey: ['ingestion-sources'],
    queryFn: async () => (await apiClient.get<Source[]>('/data-sources')).data,
    retry: false,
  })
  const history = useQuery({
    queryKey: ['import-history', filter, typeFilter, fromDate, toDate],
    queryFn: async () => (await apiClient.get<ImportRecord[]>('/imports', {
      params: { import_status: filter || undefined, source_type: typeFilter || undefined, from_date: fromDate || undefined, to_date: toDate || undefined },
    })).data,
    retry: false,
  })
  const datasets = useQuery({
    queryKey: ['ingestion-datasets'],
    queryFn: async () => (await apiClient.get<Dataset[]>('/datasets')).data,
    retry: false,
  })
  const connections = useQuery({
    queryKey: ['source-connections'],
    queryFn: async () => (await apiClient.get<Connection[]>('/imports/connections')).data,
    retry: false,
  })
  function availableConnections(type: string) {
    const kind = type.toLowerCase() === 'rest api' ? 'rest' : type.toLowerCase() === 'postgresql' ? 'postgresql' : null
    return connections.data?.filter(connection => connection.kind === kind) ?? []
  }
  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['ingestion-sources'] }),
      queryClient.invalidateQueries({ queryKey: ['import-history'] }),
      queryClient.invalidateQueries({ queryKey: ['ingestion-datasets'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard-snapshot'] }),
    ])
  }
  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true); setNotice('')
    try {
      await apiClient.post('/data-sources', {
        name: values.get('name'), source_type: values.get('source_type'),
        description: values.get('description') || null,
        connection_ref: values.get('connection_ref') || null,
      })
      form.reset()
      setSourceType('CSV')
      setNotice('Source registered.')
      await refresh()
    } catch (error) { setNotice(message(error)) } finally { setBusy(false) }
  }
  async function updateSource(event: FormEvent<HTMLFormElement>, source: Source) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    setBusy(true); setNotice('')
    try {
      await apiClient.patch(`/data-sources/${source.id}`, {
        name: values.get('name'), description: values.get('description') || null,
        status: values.get('status'), connection_ref: values.get('connection_ref') || null,
      })
      setEditing(null)
      setNotice('Source updated.')
      await refresh()
    } catch (error) { setNotice(message(error)) } finally { setBusy(false) }
  }
  async function deleteSource(source: Source) {
    if (!window.confirm(`Delete "${source.name}"? Datasets will be unlinked; import history is retained.`)) return
    setBusy(true); setNotice('')
    try {
      await apiClient.delete(`/data-sources/${source.id}`)
      setNotice('Source deleted.')
      await refresh()
    } catch (error) { setNotice(message(error)) } finally { setBusy(false) }
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    setBusy(true); setNotice('')
    try {
      const result = await apiClient.post<ImportRecord>('/imports/files', new FormData(form))
      setNotice(`Imported ${result.data.records_received.toLocaleString()} records.`)
      form.reset()
    } catch (error) { setNotice(message(error)) } finally {
      await refresh()
      setBusy(false)
    }
  }
  async function importConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    setBusy(true); setNotice('')
    try {
      const result = await apiClient.post<ImportRecord>('/imports/connections', {
        source_id: values.get('source_id'), dataset_name: values.get('dataset_name'),
        schema_type: values.get('schema_type'),
      }, { timeout: 60_000 })
      setNotice(`Imported ${result.data.records_received.toLocaleString()} records from the configured connection.`)
      form.reset()
    } catch (error) { setNotice(message(error)) } finally {
      await refresh()
      setBusy(false)
    }
  }
  return <div className="page-enter ingestion-workspace">
    <div className="page-header">
      <div><div className="eyebrow"><span className="eyebrow-line" /> DATA MANAGEMENT / WORKSPACE</div>
        <h1>{page === 'sources' ? 'Data Sources' : 'Data Ingestion'}<span className="heading-period">.</span></h1>
        <p>{page === 'sources' ? 'Register and review your shared data sources.' : 'Import synthetic datasets and review their history.'}</p>
      </div>
      <span className="preview-pill"><Database size={14} /> SHARED WORKSPACE</span>
    </div>
      <div className="demo-notice"><span className="demo-notice-icon"><Database size={16} /></span>
        <p><strong>Unprotected development workspace.</strong><span> Anyone with API access can change shared data. Upload synthetic data only; originals are stored locally on the API server.</span></p>
      </div>
      {notice && <div className="ingestion-message" role="status">{notice}</div>}
      {(sources.isError || history.isError || datasets.isError || connections.isError) && <div className="ingestion-message" role="alert">Could not load workspace data. Check the API connection.</div>}
      {page === 'sources' ? <div className="ingestion-grid">
        <section className="panel ingestion-panel"><div className="section-kicker">SOURCE INVENTORY</div><h2>Registered sources</h2>
          <div className="ingestion-list">{sources.data?.map(source => <article key={source.id}>
            {editing === source.id ? <form className="ingestion-form ingestion-edit" onSubmit={event => { void updateSource(event, source) }}>
              <label>Source name<input name="name" defaultValue={source.name} required maxLength={120} /></label>
              <label>Description<textarea name="description" defaultValue={source.description ?? ''} maxLength={500} rows={2} /></label>
              <label>Source state<select name="status" defaultValue={source.status}><option value="active">Active</option><option value="inactive">Inactive</option><option value="error">Error</option></select></label>
              {['rest api', 'postgresql'].includes(source.source_type.toLowerCase()) && <label>Configured connection<select name="connection_ref" defaultValue={source.connection_ref ?? ''}><option value="">Not configured</option>{source.connection_ref && !availableConnections(source.source_type).some(c => c.reference === source.connection_ref) && <option value={source.connection_ref}>{source.connection_ref} (unavailable)</option>}{availableConnections(source.source_type).map(c => <option key={c.reference} value={c.reference}>{c.reference}</option>)}</select></label>}
              <div className="ingestion-actions"><button className="button button-primary" disabled={busy} type="submit">Save</button><button className="button" disabled={busy} onClick={() => setEditing(null)} type="button">Cancel</button></div>
            </form> : <>
              <div><strong>{source.name}</strong><span>{source.source_type} · {source.status}</span>{source.description && <small>{source.description}</small>}{source.connection_ref && <small>Connection: {source.connection_ref}</small>}<div className="ingestion-actions"><button className="button button-small" disabled={busy} onClick={() => setEditing(source.id)} type="button">Edit</button><button className="button button-small" disabled={busy} onClick={() => { void deleteSource(source) }} type="button">Delete</button></div></div>
              <div><strong>{source.records_count.toLocaleString()} records</strong><span>Last import {formatDate(source.last_synced_at)}</span><small>Added {formatDate(source.created_at)}</small></div>
            </>}
          </article>)}{sources.isLoading && <p>Loading sources…</p>}{sources.data?.length === 0 && <p>No sources registered yet.</p>}</div>
        </section>
        <section className="panel ingestion-panel"><div className="section-kicker">NEW SOURCE</div><h2>Register a source</h2>
          <form className="ingestion-form" onSubmit={register}>
            <label>Source name<input name="name" required maxLength={120} /></label>
            <label>Source type<select name="source_type" value={sourceType} onChange={event => setSourceType(event.target.value)}><option>CSV</option><option>Excel</option><option>JSON</option><option>REST API</option><option>PostgreSQL</option></select></label>
            <label>Description<textarea name="description" maxLength={500} rows={3} /></label>
            {['REST API', 'PostgreSQL'].includes(sourceType) && <label>Configured connection<select name="connection_ref" defaultValue="" required><option value="" disabled>Select a configured connection</option>{availableConnections(sourceType).map(c => <option key={c.reference} value={c.reference}>{c.reference}</option>)}</select></label>}
            <p>REST and PostgreSQL connections must be configured on the server first. Credentials are never entered here.</p>
            <button className="button button-primary" disabled={busy} type="submit">Register source</button>
          </form>
        </section>
      </div> : <>
        <div className="ingestion-grid">
          <section className="panel ingestion-panel"><div className="section-kicker">BRONZE INTAKE</div><h2>Upload a dataset</h2>
            <form className="ingestion-form" onSubmit={upload}>
              <label>File source<select name="source_id" required defaultValue=""><option value="" disabled>Select a source</option>{sources.data?.filter(s => ['csv', 'excel', 'json'].includes(s.source_type.toLowerCase()) && s.status !== 'inactive').map(s => <option key={s.id} value={s.id}>{s.name} · {s.source_type}</option>)}</select></label>
              <label>Dataset name<input name="dataset_name" required maxLength={120} /></label>
              <label>Data schema<select name="schema_type"><option value="aggregate">Programme aggregates</option><option value="participation">Synthetic participation</option><option value="generic">General-purpose records</option></select></label>
              <label>File (CSV, XLSX, XLS or JSON; max 2 MB)<input name="file" type="file" accept=".csv,.xlsx,.xls,.json" required /></label>
              <p>Choose aggregate, synthetic participation, or general-purpose records for later ETL validation. JSON must be an array of objects. Original files are preserved in Bronze.</p>
              <button className="button button-primary" disabled={busy} type="submit"><UploadCloud size={14} /> {busy ? 'Importing…' : 'Import dataset'}</button>
            </form>
          </section>
          <section className="panel ingestion-panel"><div className="section-kicker">CONNECTED SOURCES</div><h2>Import from a connection</h2>
            <form className="ingestion-form" onSubmit={importConnection}>
              <label>Connected source<select name="source_id" required defaultValue=""><option value="" disabled>Select a source</option>{sources.data?.filter(s => ['rest api', 'postgresql'].includes(s.source_type.toLowerCase()) && s.status !== 'inactive' && s.connection_ref).map(s => <option key={s.id} value={s.id}>{s.name} · {s.source_type}</option>)}</select></label>
              <label>Dataset name<input name="dataset_name" required maxLength={120} /></label>
              <label>Data schema<select name="schema_type"><option value="aggregate">Programme aggregates</option><option value="participation">Synthetic participation</option><option value="generic">General-purpose records</option></select></label>
              <p>REST sources must return a JSON array. PostgreSQL imports save a JSON snapshot of the configured table.</p>
              <button className="button button-primary" disabled={busy} type="submit"><Database size={14} /> {busy ? 'Importing…' : 'Import connection'}</button>
            </form>
          </section>
          <section className="panel ingestion-panel"><div className="section-kicker">DATASET CATALOGUE</div><h2>Registered datasets</h2>
            <div className="ingestion-list">{datasets.data?.map(dataset => <article key={dataset.id}><div><strong>{dataset.name}</strong><span>Added {formatDate(dataset.created_at)}</span></div></article>)}{datasets.data?.length === 0 && <p>No datasets registered yet.</p>}</div>
          </section>
        </div>
        <section className="panel ingestion-panel ingestion-history"><div className="section-kicker">IMPORT ACTIVITY</div><h2>Ingestion history</h2>
          <div className="ingestion-filters">
            <label>Status<select value={filter} onChange={event => setFilter(event.target.value)}><option value="">All statuses</option><option value="succeeded">Succeeded</option><option value="failed">Failed</option><option value="running">Running</option></select></label>
            <label>Source type<select value={typeFilter} onChange={event => setTypeFilter(event.target.value)}><option value="">All types</option><option>CSV</option><option>Excel</option><option>JSON</option><option>REST API</option><option>PostgreSQL</option></select></label>
            <label>From<input type="date" value={fromDate} onChange={event => setFromDate(event.target.value)} /></label>
            <label>To<input type="date" value={toDate} onChange={event => setToDate(event.target.value)} /></label>
          </div>
          <div className="ingestion-list">{history.data?.map(item => <article key={item.id}><div><strong>{item.dataset_name}</strong><span>{item.source_name} · {item.source_type} · {formatDate(item.created_at)}</span>{item.error_message && <small className="ingestion-error">{item.error_message}</small>}</div><div><strong>{item.status}</strong><span>{item.records_received.toLocaleString()} records</span></div></article>)}{history.isLoading && <p>Loading history…</p>}{history.data?.length === 0 && <p>No imports match these filters.</p>}</div>
        </section>
    </>}
  </div>
}
