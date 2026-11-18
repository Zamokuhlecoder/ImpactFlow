import { describe, expect, it } from 'vitest'
import { MAX_CSV_BYTES, parseProgrammeCsv, SAMPLE_CSV } from './programmeCsv'

describe('programme CSV', () => {
  it('parses the synthetic sample and quoted fields with accurate aggregates', () => {
    const sample = parseProgrammeCsv(SAMPLE_CSV)
    expect(sample).toHaveLength(6)
    expect(sample.reduce((total, row) => total + row.reached, 0)).toBe(12885)
    const csv = 'name,category,province,target_beneficiaries,reached_beneficiaries,status\r\n"Learning, Support",Education,Gauteng,10,7,active\r\n'
    expect(parseProgrammeCsv(csv)[0]).toEqual({
      name: 'Learning, Support', category: 'Education', province: 'Gauteng', target: 10, reached: 7, status: 'active',
    })
  })

  it('rejects malformed, personal, invalid or oversized input', () => {
    const header = 'name,category,province,target_beneficiaries,reached_beneficiaries'
    expect(() => parseProgrammeCsv(`${header},email\nA,Education,Gauteng,10,7,x@example.com`)).toThrow('Unsupported columns')
    expect(() => parseProgrammeCsv(`${header}\nA,Education,Gauteng,10,-1`)).toThrow('non-negative integer')
    expect(() => parseProgrammeCsv(`${header}\nA,Education,Nowhere,10,7`)).toThrow('province')
    expect(() => parseProgrammeCsv(`${header}\nA,Education,Gauteng,10,7\nA,Education,Gauteng,20,5`)).toThrow('unique')
    expect(() => parseProgrammeCsv(`${header}\n"unfinished,Education,Gauteng,10,7`)).toThrow('Invalid CSV')
    expect(() => parseProgrammeCsv('x'.repeat(MAX_CSV_BYTES + 1))).toThrow('2 MB')
  })
})
