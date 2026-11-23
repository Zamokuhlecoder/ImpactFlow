import {
  Activity, BarChart3, Database, FileClock, FileText, GitBranch, HardDrive,
  Layers3, LayoutDashboard, LineChart, Settings, ShieldCheck, Table2, UploadCloud, Workflow,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface ModuleDefinition {
  path: string
  label: string
  group: string
  icon: LucideIcon
  description: string
  focus: string
  capabilities: string[]
}

export const modules: ModuleDefinition[] = [
  { path: '/', label: 'Overview', group: 'Workspace', icon: LayoutDashboard, description: 'Your data operations, at a glance.', focus: '', capabilities: [] },
  { path: '/data-sources', label: 'Data Sources', group: 'Data management', icon: Database, description: 'Bring your operational data together in one place.', focus: 'Source inventory', capabilities: ['File uploads', 'API connections', 'Database connections'] },
  { path: '/data-ingestion', label: 'Data Ingestion', group: 'Data management', icon: UploadCloud, description: 'Track how data enters the platform.', focus: 'Ingestion activity', capabilities: ['Format detection', 'File validation', 'Ingestion history'] },
  { path: '/data-processing', label: 'ETL Processing', group: 'Data management', icon: Layers3, description: 'Transform Bronze data into trusted analytics datasets.', focus: 'Bronze to Gold processing', capabilities: ['Standardisation and validation', 'Quarantine and quality reports', 'Gold analytics datasets'] },
  { path: '/data-pipelines', label: 'Data Pipelines', group: 'Data management', icon: Workflow, description: 'Explore the flow from raw data to useful insight.', focus: 'Pipeline runs', capabilities: ['Extract and load', 'Transformation', 'Execution history'] },
  { path: '/data-lake', label: 'Data Lake', group: 'Data management', icon: HardDrive, description: 'Organise data through the medallion architecture.', focus: 'Storage layers', capabilities: ['Bronze · raw data', 'Silver · validated data', 'Gold · curated data'] },
  { path: '/data-warehouse', label: 'Data Warehouse', group: 'Data management', icon: Table2, description: 'Shape trusted data for reporting and analysis.', focus: 'Warehouse model', capabilities: ['Dimension tables', 'Fact tables', 'Reporting views'] },
  { path: '/data-quality', label: 'Data Quality', group: 'Intelligence', icon: ShieldCheck, description: 'Understand the quality of data across your organisation.', focus: 'Quality over time', capabilities: ['Validation rules', 'Duplicate detection', 'Quarantine and review'] },
  { path: '/analytics', label: 'M&E Analytics', group: 'Intelligence', icon: BarChart3, description: 'Connect programme delivery to measurable outcomes.', focus: 'Programme performance', capabilities: ['Indicator definitions', 'Targets and baselines', 'Outcome reporting'] },
  { path: '/reports', label: 'Reports', group: 'Intelligence', icon: FileText, description: 'Turn curated data into meaningful reports.', focus: 'Reporting domains', capabilities: ['Executive performance', 'Programme outcomes', 'Beneficiary reach'] },
  { path: '/predictive-analytics', label: 'Predictive Analytics', group: 'Intelligence', icon: LineChart, description: 'Explore the future of evidence-led planning.', focus: 'Model lifecycle', capabilities: ['Synthetic training data', 'Target risk modelling', 'Evaluation and limitations'] },
  { path: '/monitoring', label: 'Monitoring', group: 'Operations', icon: Activity, description: 'Keep an eye on execution and operational activity.', focus: 'Recent executions', capabilities: ['Pipeline status', 'Failure tracking', 'System health'] },
  { path: '/orchestration', label: 'Orchestration', group: 'Operations', icon: Workflow, description: 'Schedule, trigger and investigate Airflow workflows.', focus: 'DAG execution', capabilities: ['Scheduled pipelines', 'Task history', 'Retry and recovery'] },
  { path: '/governance', label: 'Data Governance', group: 'Operations', icon: ShieldCheck, description: 'Build trust through clear ownership and responsible access.', focus: 'Governance foundations', capabilities: ['Ownership and stewardship', 'Data classification', 'Access permissions'] },
  { path: '/data-lineage', label: 'Data Lineage', group: 'Operations', icon: GitBranch, description: 'Follow data from its source to its destination.', focus: 'Intended data journey', capabilities: ['Source to ingestion', 'Transformation lineage', 'Reporting dependencies'] },
  { path: '/audit-logs', label: 'Audit Logs', group: 'Operations', icon: FileClock, description: 'Make important data and access events traceable.', focus: 'Audit coverage', capabilities: ['Access events', 'Data changes', 'Administrative actions'] },
  { path: '/settings', label: 'Settings', group: 'Operations', icon: Settings, description: 'Manage your workspace and platform preferences.', focus: 'Workspace settings', capabilities: ['Organisation profile', 'User preferences', 'Environment configuration'] },
]

export const navigationGroups = ['Workspace', 'Data management', 'Intelligence', 'Operations'].map((label) => ({
  label,
  items: modules.filter((item) => item.group === label),
}))

export const architectureLayers = [
  { label: 'Bronze', detail: 'Raw source data', icon: Database },
  { label: 'Silver', detail: 'Cleaned & validated', icon: Layers3 },
  { label: 'Gold', detail: 'Analytics-ready', icon: BarChart3 },
]
