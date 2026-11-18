import Papa from 'papaparse'
import sampleCsv from './sample-programmes.csv?raw'

export const SAMPLE_CSV = sampleCsv
export const MAX_CSV_BYTES = 2 * 1024 * 1024
export const CSV_STORAGE_KEY = 'impactflow-programme-csv-v1'

const provinces = new Set([
  'Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal', 'Limpopo',
  'Mpumalanga', 'Northern Cape', 'North West', 'Western Cape',
])
const requiredColumns = ['name', 'category', 'province', 'target_beneficiaries', 'reached_beneficiaries']
const allowedColumns = new Set([...requiredColumns, 'status'])

export interface CsvProgramme {
  name: string
  category: string
  province: string
  target: number
  reached: number
  status: 'active' | 'inactive'
}

export function parseProgrammeCsv(text: string): CsvProgramme[] {
  if (new TextEncoder().encode(text).length > MAX_CSV_BYTES) throw new Error('CSV must be 2 MB or smaller.')
  const parsed = Papa.parse<string[]>(text.replace(/^\uFEFF/, ''), { skipEmptyLines: 'greedy' })
  if (parsed.errors.length) throw new Error(`Invalid CSV: ${parsed.errors[0].message}`)
  const [header, ...rows] = parsed.data
  if (!header || !rows.length) throw new Error('CSV must contain a header and at least one programme.')
  if (rows.length > 2000) throw new Error('CSV must contain no more than 2,000 programmes.')
  const columns = header.map((column) => column.trim())
  if (new Set(columns).size !== columns.length) throw new Error('CSV contains duplicate column names.')
  const missing = requiredColumns.filter((column) => !columns.includes(column))
  if (missing.length) throw new Error(`Missing columns: ${missing.join(', ')}.`)
  const unsupported = columns.filter((column) => !allowedColumns.has(column))
  if (unsupported.length) throw new Error(`Unsupported columns: ${unsupported.join(', ')}. Do not upload personal data.`)
  const names = new Set<string>()
  return rows.map((row, index) => {
    const rowNumber = index + 2
    if (row.length !== columns.length) throw new Error(`Row ${rowNumber} has the wrong number of columns.`)
    const value = (column: string) => row[columns.indexOf(column)]?.trim() ?? ''
    const name = value('name')
    const category = value('category')
    const province = value('province')
    const status = value('status') || 'active'
    if (!name || name.length > 120 || !category || category.length > 80) {
      throw new Error(`Row ${rowNumber}: name and category are required (maximum 120 and 80 characters).`)
    }
    if (names.has(name.toLocaleLowerCase('en-ZA'))) throw new Error(`Row ${rowNumber}: programme names must be unique.`)
    names.add(name.toLocaleLowerCase('en-ZA'))
    if (!provinces.has(province)) throw new Error(`Row ${rowNumber}: province must be a South African province.`)
    if (status !== 'active' && status !== 'inactive') throw new Error(`Row ${rowNumber}: status must be active or inactive.`)
    const count = (column: string) => {
      const input = value(column)
      const number = Number(input)
      if (!/^\d+$/.test(input) || !Number.isSafeInteger(number) || number > 2147483647) {
        throw new Error(`Row ${rowNumber}: ${column} must be a non-negative integer up to 2147483647.`)
      }
      return number
    }
    return { name, category, province, status, target: count('target_beneficiaries'), reached: count('reached_beneficiaries') }
  })
}
