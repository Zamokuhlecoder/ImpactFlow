export const WORLD_BANK_POPULATION_URL = 'https://api.worldbank.org/v2/country/ZAF/indicator/SP.POP.TOTL?format=json&per_page=20'

export interface PopulationObservation {
  year: string
  value: number
}

export async function getSouthAfricaPopulation(signal?: AbortSignal): Promise<PopulationObservation> {
  const response = await fetch(WORLD_BANK_POPULATION_URL, { credentials: 'omit', signal })
  if (!response.ok) throw new Error(`World Bank request failed (${response.status}).`)
  const data: unknown = await response.json()
  if (!Array.isArray(data) || !Array.isArray(data[1])) throw new Error('Unexpected World Bank response.')
  for (const row of data[1] as unknown[]) {
    if (typeof row === 'object' && row !== null && 'date' in row && 'value' in row
      && typeof row.date === 'string' && /^\d{4}$/.test(row.date)
      && typeof row.value === 'number' && Number.isFinite(row.value)) {
      return { year: row.date, value: row.value }
    }
  }
  throw new Error('No recent population observation is available.')
}
