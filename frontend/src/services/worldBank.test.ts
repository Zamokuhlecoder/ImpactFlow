import { afterEach, describe, expect, it, vi } from 'vitest'
import { getSouthAfricaPopulation } from './worldBank'

afterEach(() => vi.unstubAllGlobals())

describe('World Bank population', () => {
  it('uses the latest available national observation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{}, [{ date: '2026', value: null }, { date: '2025', value: 12345 }]],
    }))
    expect(await getSouthAfricaPopulation()).toEqual({ year: '2025', value: 12345 })
    expect(fetch).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ credentials: 'omit' }))
  })

  it('reports an unavailable or malformed public response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    await expect(getSouthAfricaPopulation()).rejects.toThrow('503')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }))
    await expect(getSouthAfricaPopulation()).rejects.toThrow('Unexpected')
  })
})
