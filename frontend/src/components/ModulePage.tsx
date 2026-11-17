import { ArrowRight, CircleDashed, FileClock, FlaskConical, Layers3, LockKeyhole } from 'lucide-react'
import { Link } from 'react-router-dom'
import { architectureLayers, type ModuleDefinition } from '../data/navigation'
import type { DashboardSnapshot } from '../types/dashboard'
import { ExecutionTable } from './ExecutionTable'
import { SectionHeading } from './SectionHeading'

interface ModulePageProps {
  module: ModuleDefinition
  snapshot: DashboardSnapshot
  search: string
}

export function ModulePage({ module, snapshot, search }: ModulePageProps) {
  const isPipeline = module.path === '/data-pipelines' || module.path === '/monitoring'
  const isAnalytics = module.path === '/analytics'
  const isQuality = module.path === '/data-quality'
  const isLake = module.path === '/data-lake'
  const isWarehouse = module.path === '/data-warehouse'
  const isLineage = module.path === '/data-lineage'
  const isSources = module.path === '/data-sources' || module.path === '/data-ingestion'
  const isAudit = module.path === '/audit-logs'
  const isSettings = module.path === '/settings'
  const isReports = module.path === '/reports'
  const isPredictive = module.path === '/predictive-analytics'
  const isGovernance = module.path === '/governance'
  const mainTitle = isAnalytics ? 'Programme target achievement' : isQuality ? 'Example quality checks' : isLake ? 'The data journey' : isSources ? 'Example operational sources' : isWarehouse ? 'Planned star schema' : isLineage ? 'Intended lineage' : isAudit ? 'Audit event stream' : isSettings ? 'Workspace profile' : isReports ? 'Reporting domains' : isPredictive ? 'Model development lifecycle' : isGovernance ? 'Governance framework' : 'Capability roadmap'

  return (
    <div className="module-page page-enter">
      <div className="page-header">
        <div><div className="eyebrow"><span className="eyebrow-line" /> {module.group.toUpperCase()} / PREVIEW</div><h1>{module.label}</h1><p>{module.description}</p></div>
        <span className="preview-pill"><FlaskConical size={14} /> DESIGN PREVIEW</span>
      </div>
      <div className="demo-notice"><span className="demo-notice-icon"><CircleDashed size={16} /></span><p><strong>Preview only</strong><span> This module is not connected or operational. Any figures shown are synthetic examples.</span></p></div>
      <div className="module-hero panel">
        <div className="module-hero-copy"><span className="section-kicker">EXPLORE THE WORKSPACE</span><h2>{module.focus}</h2><p>{module.description} This preview illustrates the intended experience while the underlying services are planned.</p><span className="preview-status"><span /> PLANNED CAPABILITY</span></div>
        <div className="module-hero-icon"><module.icon size={58} strokeWidth={1.1} /></div>
      </div>
      <div className="module-grid">
        <article className="panel module-main">
          <SectionHeading title={mainTitle} subtitle={isAnalytics || isQuality || isSources || isSettings ? 'Illustrative synthetic examples' : 'Planned platform design'} />
          {isAnalytics ? <div className="progress-list">{snapshot.programmePerformance.map((item) => <div className="progress-item" key={item.programme}><div><span>{item.programme}</span><strong>{item.achievement}% <small>/ {item.target}% target</small></strong></div><div className="progress-track"><span style={{ width: `${item.achievement}%` }} /></div></div>)}</div>
            : isQuality ? <div className="quality-preview"><div className="quality-number"><strong>{snapshot.metrics.qualityScore}%</strong><span>Example quality score</span></div><div className="quality-checks">{['Completeness', 'Validity', 'Uniqueness'].map((name, index) => <div key={name}><span>{name}</span><div className="progress-track"><span style={{ width: `${[96, 91, 98][index]}%` }} /></div><strong>{[96, 91, 98][index]}%</strong></div>)}</div></div>
            : isLake ? <div className="layer-list">{architectureLayers.map((layer, index) => <div className="layer-item" key={layer.label}><span className="layer-number">0{index + 1}</span><span className="layer-icon"><layer.icon size={20} /></span><div><strong>{layer.label}</strong><span>{layer.detail}</span></div>{index < 2 && <ArrowRight className="layer-arrow" size={16} />}</div>)}</div>
            : isSources ? <div className="source-list">{Array.from(new Set(snapshot.executions.map((run) => run.source))).map((source, index) => <div key={source}><span className="source-icon"><Layers3 size={16} /></span><span><strong>{source}</strong><small>Example {index % 2 ? 'file' : 'data source'}</small></span><span className="sample-tag">SYNTHETIC</span></div>)}</div>
            : isWarehouse ? <div className="schema-preview"><div><span className="section-kicker">DIMENSIONS</span>{['Beneficiary', 'Programme', 'Location', 'Date', 'Organisation', 'Indicator'].map((name) => <span className="schema-chip" key={name}>{name}</span>)}</div><div><span className="section-kicker">FACTS</span>{['Participation', 'Outcomes', 'Expenditure', 'Assessments'].map((name) => <span className="schema-chip fact-chip" key={name}>{name}</span>)}</div></div>
            : isLineage ? <div className="lineage-flow">{['Operational sources', 'Ingestion', 'Transformations', 'Reporting'].map((name, index) => <div key={name}><span className="lineage-step">0{index + 1}</span><strong>{name}</strong>{index < 3 && <ArrowRight size={15} />}</div>)}</div>
            : isAudit ? <div className="module-empty"><span><FileClock size={23} /></span><strong>No audit events available</strong><p>Audit collection and storage have not been implemented yet.</p></div>
            : isSettings ? <div className="settings-preview"><div><span>Organisation</span><strong>Impact Development Foundation</strong></div><div><span>Workspace</span><strong>Development demo</strong></div><div><span>Authentication</span><strong>Not configured</strong></div><p>These are display examples; settings cannot be changed in this preview.</p></div>
            : isReports ? <div className="report-grid">{module.capabilities.map((name, index) => <div key={name}><span className="layer-icon"><BarChart3Icon index={index} /></span><strong>{name}</strong><small>Reporting view planned</small><span className="sample-tag">NOT AVAILABLE</span></div>)}</div>
            : isPredictive ? <div className="lineage-flow">{['Synthetic data', 'Training', 'Evaluation', 'Risk insights'].map((name, index) => <div key={name}><span className="lineage-step">0{index + 1}</span><strong>{name}</strong>{index < 3 && <ArrowRight size={15} />}</div>)}</div>
            : isGovernance ? <div className="report-grid">{['Ownership', 'Classification', 'Access control'].map((name, index) => <div key={name}><span className="layer-icon"><BarChart3Icon index={index} /></span><strong>{name}</strong><small>Policy and controls planned</small><span className="sample-tag">PLANNED</span></div>)}</div>
            : <div className="capability-list">{module.capabilities.map((item, index) => <div key={item}><span className="capability-number">0{index + 1}</span><div><strong>{item}</strong><span>Planned for a future implementation phase</span></div><span className="sample-tag">PLANNED</span></div>)}</div>}
        </article>
        <article className="panel module-side">
          <SectionHeading title="What's planned" subtitle="A closer look at this module" />
          <div className="feature-list">{module.capabilities.map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item}</strong><CircleDashed size={15} /></div>)}</div>
          <div className="module-info"><LockKeyhole size={17} /><div><strong>Built with trust in mind</strong><p>No live data or service connection is present in this preview.</p></div></div>
          <Link className="overview-link" to="/">Return to overview <ArrowRight size={14} /></Link>
        </article>
      </div>
      {isPipeline && <ExecutionTable executions={snapshot.executions} search={search} />}
    </div>
  )
}

function BarChart3Icon({ index }: { index: number }) {
  const icons = [Layers3, FlaskConical, LockKeyhole]
  const Icon = icons[index % icons.length]
  return <Icon size={18} />
}
