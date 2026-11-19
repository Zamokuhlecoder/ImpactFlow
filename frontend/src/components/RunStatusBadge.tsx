export function RunStatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase().replaceAll(' ', '-')
  return <span className={`status-badge status-${normalized}`}><span />{status}</span>
}
