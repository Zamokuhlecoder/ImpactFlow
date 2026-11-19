import { useMemo } from 'react'

export function RecordTable({
  records,
  emptyMessage = 'No records available.',
}: {
  records: Array<Record<string, unknown>>
  emptyMessage?: string
}) {
  const columns = useMemo(
    () => [...new Set(records.flatMap(record => Object.keys(record)))],
    [records],
  )

  if (!records.length) return <p className="processing-empty">{emptyMessage}</p>
  return <>
    <div className="processing-table-wrap">
      <table className="processing-table">
        <thead><tr>{columns.map(column => <th key={column} scope="col">{column.replaceAll('_', ' ')}</th>)}</tr></thead>
        <tbody>{records.slice(0, 50).map((record, index) => <tr key={index}>
          {columns.map(column => {
            const value = record[column]
            return <td key={column}>{value === null || value === undefined
              ? '—'
              : typeof value === 'object'
                ? JSON.stringify(value)
                : String(value)}</td>
          })}
        </tr>)}</tbody>
      </table>
    </div>
    {records.length > 50 && <p className="processing-table-note">Showing the first 50 of {records.length.toLocaleString()} records.</p>}
  </>
}
