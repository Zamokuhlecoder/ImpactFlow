import { useReducedMotion } from 'framer-motion'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DashboardSnapshot } from '../types/dashboard'
import { SectionHeading } from './SectionHeading'

const colors = { purple: '#A78BFA', success: '#22C55E', warning: '#FACC15', error: '#F43F5E', info: '#38BDF8' }
const axis = { fill: '#A5A0B8', fontSize: 11 }
const grid = 'rgba(167,139,250,0.10)'
const numberFormatter = new Intl.NumberFormat('en-ZA')
const compactNumber = (value: number) => value >= 1000
  ? `${new Intl.NumberFormat('en-ZA', { maximumFractionDigits: 1 }).format(value / 1000)}k`
  : numberFormatter.format(value)

type TooltipEntry = { name?: string; value?: number | string; color?: string }
function ChartTooltip({ active, payload, label, suffix = '' }: { active?: boolean; payload?: TooltipEntry[]; label?: string; suffix?: string }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label || 'Pipeline status'}</strong>{payload.map((item, index) => <span key={`${item.name}-${index}`}><i style={{ background: item.color }} />{item.name}: <b>{typeof item.value === 'number' ? numberFormatter.format(item.value) : item.value}{suffix}</b></span>)}</div>
}

function ChartCard({ title, subtitle, children, className = '', action }: { title: string; subtitle: string; children: React.ReactNode; className?: string; action?: React.ReactNode }) {
  return <article className={`panel chart-card entrance-card ${className}`}><SectionHeading title={title} subtitle={subtitle} action={action} />{children}</article>
}

function Legend({ items }: { items: Array<{ label: string; color: string }> }) {
  return <div className="chart-legend">{items.map((item) => <span key={item.label}><i style={{ background: item.color }} />{item.label}</span>)}</div>
}

interface DashboardChartsProps {
  snapshot: DashboardSnapshot
  visibleIngestion: DashboardSnapshot['ingestionTrend']
  days: number
  mode: 'api' | 'demo'
}

export default function DashboardCharts({ snapshot, visibleIngestion, days, mode }: DashboardChartsProps) {
  const reduceMotion = useReducedMotion()
  const runs = snapshot.pipelineRuns.slice(-days)
  const status = [
    { name: 'Succeeded', value: runs.reduce((sum, item) => sum + item.succeeded, 0), color: colors.success },
    { name: 'Running', value: runs.reduce((sum, item) => sum + item.running, 0), color: colors.info },
    { name: 'Warning', value: runs.reduce((sum, item) => sum + item.warning, 0), color: colors.warning },
    { name: 'Failed', value: runs.reduce((sum, item) => sum + item.failed, 0), color: colors.error },
  ]
  const total = status.reduce((sum, item) => sum + item.value, 0)
  const ingestionTotal = visibleIngestion.reduce((sum, item) => sum + item.records, 0)
  const animateChart = !reduceMotion
  const runLegend = [{ label: 'Succeeded', color: colors.success }, { label: 'Running', color: colors.info }, { label: 'Warning', color: colors.warning }, { label: 'Failed', color: colors.error }]
  const dataLabel = mode === 'api' ? 'API DATA' : 'DEMO DATA'

  return (
    <section aria-label="Operational and programme charts" className="chart-grid">
      <ChartCard title="Data pipeline runs" subtitle={`Execution activity · last ${days} days`} className="runs-panel" action={<span className="panel-context">{dataLabel}</span>}>
        <Legend items={runLegend} />
        <p className="sr-only">For the selected period: {status.map((item) => `${item.name}: ${item.value}`).join(', ')}.</p>
        {mode === 'api' && total === 0 ? <div className="chart-empty">No pipeline execution records in this range.</div> : <div className="chart-area chart-large">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={runs} margin={{ top: 10, right: 6, left: -20, bottom: 0 }} barGap={1}>
              <CartesianGrid stroke={grid} vertical={false} strokeDasharray="3 5" />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={axis} minTickGap={35} />
              <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={axis} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(167,139,250,0.06)' }} />
              <Bar dataKey="succeeded" name="Succeeded" stackId="runs" fill={colors.success} isAnimationActive={animateChart} />
              <Bar dataKey="running" name="Running" stackId="runs" fill={colors.warning} isAnimationActive={animateChart} />
              <Bar dataKey="warning" name="Warning" stackId="runs" fill={colors.warning} isAnimationActive={animateChart} />
              <Bar dataKey="failed" name="Failed" stackId="runs" fill={colors.error} radius={[3, 3, 0, 0]} isAnimationActive={animateChart} />
            </BarChart>
          </ResponsiveContainer>
        </div>}
      </ChartCard>

      <ChartCard title="Pipeline execution status" subtitle={`Execution totals · last ${days} days`} className="status-panel">
        {mode === 'api' && total === 0 ? <div className="chart-empty chart-empty-compact">No pipeline execution records in this range.</div> : <div className="status-breakdown">
          <div aria-label={`${numberFormatter.format(total)} total runs`} className="status-breakdown-bar">
            {status.filter(item => item.value > 0).map(item => <span
              key={item.name}
              style={{ background: item.color, width: `${item.value / total * 100}%` }}
              title={`${item.name}: ${numberFormatter.format(item.value)}`}
            />)}
          </div>
          <div className="status-breakdown-total"><strong>{numberFormatter.format(total)}</strong><span>recorded executions</span></div>
          <div className="status-breakdown-list">{status.map((item) => <div className="legend-row" key={item.name}><i style={{ background: item.color }} /><span>{item.name}</span><strong>{numberFormatter.format(item.value)}</strong></div>)}</div>
        </div>}
      </ChartCard>

      <ChartCard title="Data quality trend" subtitle="Quality score · latest recorded snapshots" className="quality-panel" action={<span className="chart-highlight">{snapshot.metrics.qualityScore}% <small>current</small></span>}>
        {mode === 'api' && snapshot.qualityTrend.length === 0 ? <div className="chart-empty">No quality snapshots have been recorded.</div> : <div className="chart-area chart-medium">
          <ResponsiveContainer width="100%" height="100%"><AreaChart data={snapshot.qualityTrend} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
            <defs><linearGradient id="quality-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={colors.purple} stopOpacity={0.2} /><stop offset="100%" stopColor={colors.purple} stopOpacity={0.01} /></linearGradient></defs>
            <CartesianGrid stroke={grid} vertical={false} strokeDasharray="3 5" />
            <XAxis axisLine={false} dataKey="day" tickLine={false} tick={axis} minTickGap={28} />
            <YAxis axisLine={false} domain={[0, 100]} tickLine={false} tick={axis} tickFormatter={(value: number) => `${value}%`} />
            <Tooltip content={<ChartTooltip suffix="%" />} />
            <Area name="Quality score" dataKey="score" fill="url(#quality-fill)" stroke={colors.purple} strokeWidth={2.5} type="monotone" isAnimationActive={animateChart} />
          </AreaChart></ResponsiveContainer>
        </div>}
      </ChartCard>

      <ChartCard title="Programme performance" subtitle="Actual achievement against target" className="programme-panel">
        <Legend items={[{ label: 'Actual', color: colors.purple }, { label: 'Target', color: 'rgba(167,139,250,0.28)' }]} />
        <p className="sr-only">{snapshot.programmePerformance.map((item) => `${item.programme}: ${item.achievement}% of ${item.target}% target`).join('; ')}.</p>
        {mode === 'api' && snapshot.programmePerformance.length === 0 ? <div className="chart-empty">No programme performance data has been recorded.</div> : <div className="chart-area chart-medium">
          <ResponsiveContainer width="100%" height="100%"><BarChart data={snapshot.programmePerformance} layout="vertical" margin={{ top: 5, right: 8, left: 0, bottom: 0 }} barGap={2}>
            <CartesianGrid stroke={grid} horizontal={false} strokeDasharray="3 5" />
            <XAxis axisLine={false} domain={[0, 100]} tickLine={false} tick={axis} tickFormatter={(value: number) => `${value}%`} type="number" />
            <YAxis axisLine={false} dataKey="programme" tickLine={false} tick={axis} type="category" tickFormatter={(value: string) => value.replace(/([a-z])([A-Z])/g, '$1 $2')} width={112} interval={0} />
            <Tooltip content={<ChartTooltip suffix="%" />} cursor={{ fill: 'rgba(167,139,250,0.06)' }} />
            <Bar name="Actual" dataKey="achievement" fill={colors.purple} radius={[0, 4, 4, 0]} barSize={8} isAnimationActive={animateChart} />
            <Bar name="Target" dataKey="target" fill="rgba(167,139,250,0.28)" radius={[0, 4, 4, 0]} barSize={8} isAnimationActive={animateChart} />
          </BarChart></ResponsiveContainer>
        </div>}
      </ChartCard>

      <ChartCard title="Data ingestion activity" subtitle={`Records ingested · last ${days} days`} className="ingestion-panel">
        <div className="chart-summary"><strong>{numberFormatter.format(ingestionTotal)}</strong><span>{mode === 'api' ? 'database records' : 'synthetic records'}</span></div>
        {mode === 'api' && ingestionTotal === 0 ? <div className="chart-empty chart-empty-compact">No ingestions were recorded in this range.</div> : <div className="chart-area chart-medium">
          <ResponsiveContainer width="100%" height="100%"><AreaChart data={visibleIngestion} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
            <defs><linearGradient id="ingestion-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={colors.info} stopOpacity={0.3} /><stop offset="100%" stopColor={colors.info} stopOpacity={0.01} /></linearGradient></defs>
            <CartesianGrid stroke={grid} vertical={false} strokeDasharray="3 5" />
            <XAxis axisLine={false} dataKey="day" tickLine={false} tick={axis} minTickGap={35} />
            <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={axis} tickFormatter={compactNumber} />
            <Tooltip content={<ChartTooltip />} />
            <Area name="Records" dataKey="records" fill="url(#ingestion-fill)" stroke={colors.info} strokeWidth={2} type="monotone" isAnimationActive={animateChart} />
          </AreaChart></ResponsiveContainer>
        </div>}
      </ChartCard>

      <ChartCard title="Beneficiaries by province" subtitle={mode === 'api' ? 'Aggregate programme reach' : 'Synthetic reach across South Africa'} className="province-panel" action={<span className="panel-context">{mode === 'api' ? 'API DATA' : '9 PROVINCES'}</span>}>
        <p className="sr-only">{snapshot.provincialReach.map((item) => `${item.province}: ${numberFormatter.format(item.beneficiaries)}`).join('; ')}.</p>
        {mode === 'api' && snapshot.provincialReach.length === 0 ? <div className="chart-empty">No aggregate provincial reach data has been recorded.</div> : <div className="chart-area chart-provinces">
          <ResponsiveContainer width="100%" height="100%"><BarChart data={snapshot.provincialReach} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={grid} horizontal={false} strokeDasharray="3 5" />
            <XAxis axisLine={false} tickLine={false} tick={axis} type="number" tickFormatter={compactNumber} />
            <YAxis axisLine={false} dataKey="province" tickLine={false} tick={axis} type="category" width={110} interval={0} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(167,139,250,0.06)' }} />
            <Bar name="Beneficiaries" dataKey="beneficiaries" fill={colors.purple} radius={[0, 4, 4, 0]} barSize={9} isAnimationActive={animateChart} />
          </BarChart></ResponsiveContainer>
        </div>}
      </ChartCard>
    </section>
  )
}
