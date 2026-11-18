import { describe, expect, it } from 'vitest'
import { isDemoSessionActive, setDemoSessionActive } from './demoSession'

describe('demo session', () => {
  it('starts active and persists sign-out until the user continues', () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => { values.set(key, value) },
      removeItem: (key: string) => { values.delete(key) },
    }

    expect(isDemoSessionActive(storage)).toBe(true)
    setDemoSessionActive(storage, false)
    expect(isDemoSessionActive(storage)).toBe(false)
    setDemoSessionActive(storage, true)
    expect(isDemoSessionActive(storage)).toBe(true)
  })
})
