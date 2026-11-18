import { useQuery } from '@tanstack/react-query'
import { BarChart3, Database, Target, UsersRound } from 'lucide-react'
import { useMemo, useState, type ChangeEvent } from 'react'
import { CSV_STORAGE_KEY, MAX_CSV_BYTES, parseProgrammeCsv, SAMPLE_CSV, type CsvProgramme } from '../data/programmeCsv'
import { getSouthAfricaPopulation } from '../services/worldBank'
import { KpiCard } from './KpiCard'
import { SectionHeading } from './SectionHeading'

interface CsvState {
  programmes: CsvProgramme[]
  uploaded: boolean
  message: string
}

function initialCsvState(): CsvState {
  const sample = parseProgrammeCsv(SAMPLE_CSV)
  if (typeof window === 'undefined') return { programmes: sample, uploaded: false, message: '' }
  try {
    const saved = window.localStorage.getItem(CSV_STORAGE_KEY)
    if (saved !== null) return { programmes: parseProgrammeCsv(saved), uploaded: true, message: 'Your saved CSV was restored from this browser.' }
    return { programmes: sample, uploaded: false, message: '' }
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Browser storage is unavailable.'
    return { programmes: sample, uploaded: false, message: `Could not restore the saved CSV: ${detail}` }
  }
}

export function CsvOverview({ search }: { search: string }) {
  const [csv, setCsv] = useState(initialCsvState)
  const [reading, setReading] = useState(false)
  const population = useQuery({
    queryKey: ['worldbank-population'],
    queryFn: ({ signal }) => getSouthAfricaPopulation(signal),
    retry: false,
    staleTime: 60 * 60 * 1000,
  })
  const totals = useMemo(() => ({
    reached: csv.programmes.reduce((total, item) => total + item.reached, 0),
    target: csv.programmes.reduce((total, item) => total + item.target, 0),
    active: csv.programmes.filter((item) => item.status === 'active').length,
  }), [csv.programmes])
  const provinces = useMemo(() => {
    const values = new Map<string, number>()
    csv.programmes.forEach((programme) => values.set(programme.province, (values.get(programme.province) ?? 0) + programme.reached))
    return [...values].sort((a, b) => b[1] - a[1])
  }, [csv.programmes])
  const matching = csv.programmes.filter((programme) =>
    `${programme.name} ${programme.category} ${programme.province}`.toLowerCase().includes(search.trim().toLowerCase()),
  )
  const format = (value: number) => new Intl.NumberFormat('en-ZA').format(value)

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget
    const file = input.files?.[0]
    input.value = ''
    if (!file) return
    setReading(true)
    try {
      if (!file.name.toLowerCase().endsWith('.csv')) throw new Error('Choose a .csv file.')
      if (file.size > MAX_CSV_BYTES) throw new Error('CSV must be 2 MB or smaller.')
      const text = await file.text()
      const programmes = parseProgrammeCsv(text)
      try {
        window.localStorage.setItem(CSV_STORAGE_KEY, text)
        setCsv({ programmes, uploaded: true, message: 'CSV loaded and saved in this browser only.' })
      } catch {
        setCsv({ programmes, uploaded: true, message: 'CSV loaded, but browser storage is unavailable. It will be lost when you leave this view or reload.' })
      }
    } catch (error) {
      setCsv((previous) => ({
        ...previous,
        message: error instanceof Error ? `CSV not loaded: ${error.message}` : 'CSV could not be read.',
      }))
    } finally {
      setReading(false)
    }
  }

  function useSample() {
    try {
      window.localStorage.removeItem(CSV_STORAGE_KEY)
      setCsv({ programmes: parseProgrammeCsv(SAMPLE_CSV), uploaded: false, message: 'Synthetic example restored.' })
    } catch {
      setCsv((previous) => ({ ...previous, message: 'Could not clear the saved CSV from browser storage.' }))
    }
  }

  return (
    <div className="page-enter">
      <div className="page-header">
        <div><div className="eyebrow"><span className="eyebrow-line" /> YOUR DATA, IN FOCUS</div><h1>Overview<span className="heading-period">.</span></h1><p>Explore aggregate programme data without signing in.</p></div>
        <div className="page-header-meta"><span className="live-indicator"><span /> {csv.uploaded ? 'BROWSER CSV' : 'SYNTHETIC EXAMPLE'}</span></div>
      </div>
      <div className="demo-notice" role="status">
        <p><strong>{csv.uploaded ? 'Uploaded CSV' : 'Synthetic example CSV'}</strong><span>Programme figures below come from {csv.uploaded ? 'your file' : 'an illustrative dataset'}, not the database. Uploads stay in this browser; use aggregate data only, never personal data.</span></p>
      </div>
      <div className="csv-controls">
        <label className="button button-primary csv-upload">Upload programme CSV<input accept=".csv,text/csv" aria-label="Upload programme CSV" disabled={reading} onChange={(event) => { void upload(event) }} type="file" /></label>
        <button className="button" disabled={reading} onClick={useSample} type="button">Use example data</button>
        <a className="button" download="impactflow-example-programmes.csv" href={`data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`}>Download example CSV</a>
      </div>
      <p className="csv-help">Required: name, category, province, target_beneficiaries, reached_beneficiaries. Optional: status. Maximum 2 MB and 2,000 rows. Uploading replaces the previous browser dataset.</p>
      {csv.message && <p className="csv-message" role="status">{csv.message}</p>}
      <section aria-label="Programme CSV metrics" className="kpi-grid">
        <KpiCard label="Total Programmes" value={csv.programmes.length} change={null} description="CSV rows" icon={BarChart3} index={0} animateValue={false} />
        <KpiCard label="Active Programmes" value={totals.active} change={null} description="in CSV" icon={Database} index={1} animateValue={false} />
        <KpiCard label="Total Reached" value={totals.reached} change={null} description="aggregate CSV count" icon={UsersRound} index={2} animateValue={false} />
        <KpiCard label="Total Target" value={totals.target} change={null} description="aggregate CSV count" icon={Target} index={3} animateValue={false} />
      </section>
      <div className="dashboard-section-title"><div><span className="section-kicker">PROGRAMME DATA</span><h2>CSV overview</h2></div><span>All programme statuses included in totals.</span></div>
      <section className="csv-grid" aria-label="Programme breakdown">
        <article className="panel csv-panel">
          <SectionHeading title="Programmes" subtitle="Aggregate rows from the selected CSV" />
          <div className="table-scroll"><table className="execution-table">
            <thead><tr><th scope="col">Programme</th><th scope="col">Category</th><th scope="col">Province</th><th scope="col">Reached</th><th scope="col">Target</th><th scope="col">Status</th></tr></thead>
            <tbody>{matching.length ? matching.map((programme) => <tr key={programme.name}><td>{programme.name}</td><td>{programme.category}</td><td>{programme.province}</td><td>{format(programme.reached)}</td><td>{format(programme.target)}</td><td>{programme.status}</td></tr>) : <tr><td className="empty-table" colSpan={6}>No programmes match your search.</td></tr>}</tbody>
          </table></div>
        </article>
        <article className="panel csv-panel">
          <SectionHeading title="Reach by province" subtitle="Sum of reached counts from CSV rows" />
          <div className="csv-provinces">{provinces.map(([province, reached]) => <div key={province}><span>{province}</span><strong>{format(reached)}</strong></div>)}</div>
        </article>
      </section>
      <article className="panel csv-context">
        <SectionHeading title="South Africa: national population" subtitle="Public context, not programme beneficiaries" action={<span className="panel-context">WORLD BANK</span>} />
        {population.isPending ? <p>Loading World Bank data…</p> : population.isError ? <p role="status">World Bank data is unavailable. <button className="account-menu-action" onClick={() => { void population.refetch() }} type="button">Retry</button></p> : <p><strong>{format(population.data.value)}</strong> people ({population.data.year})</p>}
        <a href="https://data.worldbank.org/indicator/SP.POP.TOTL?locations=ZA" target="_blank" rel="noreferrer">Source: World Bank, Population, total</a>
      </article>
    </div>
  )
}
