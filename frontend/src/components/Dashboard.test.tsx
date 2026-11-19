import { PassThrough } from 'node:stream'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { renderToPipeableStream } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Dashboard from './Dashboard'

function renderMarkup(element: ReactNode) {
  return new Promise<string>((resolve, reject) => {
    const output = new PassThrough()
    const chunks: Buffer[] = []
    output.on('data', (chunk: Buffer) => chunks.push(chunk))
    output.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    output.on('error', reject)

    const stream = renderToPipeableStream(element, {
      onAllReady: () => stream.pipe(output),
      onShellError: reject,
      onError: reject,
    })
  })
}

describe('Overview', () => {
  it('opens the database-backed view and makes the CSV view available', async () => {
    const markup = await renderMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/']}>
          <Dashboard onSignOut={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(markup).toContain('Database API')
    expect(markup).toContain('Browser CSV')
    expect(markup).toContain('Demo user')
    expect(markup).toContain('Sign out of demo')
    expect(markup).not.toContain('Latest synthetic workspace events')
  })

  describe('Data management', () => {
    it('shows source registration without requiring sign-in', async () => {
      const markup = await renderMarkup(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={['/data-sources']}>
            <Dashboard onSignOut={() => {}} />
          </MemoryRouter>
        </QueryClientProvider>,
      )
      expect(markup).toContain('Register a source')
      expect(markup).not.toContain('Sign in')
      expect(markup).not.toContain('Example operational sources')
    })

    it('renders the database-backed ETL processing workspace', async () => {
      const markup = await renderMarkup(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={['/data-processing']}>
            <Dashboard onSignOut={() => {}} />
          </MemoryRouter>
        </QueryClientProvider>,
      )

      expect(markup).toContain('ETL Processing')
      expect(markup).toContain('Select a Bronze dataset')
      expect(markup).toContain('Run transformation')
      expect(markup).not.toContain('This module is a non-operational preview')
    })

    it.each([
      ['/data-pipelines', 'Data Pipelines'],
      ['/monitoring', 'Pipeline Monitoring'],
      ['/analytics', 'Analytics'],
      ['/data-quality', 'Data Quality'],
      ['/data-lake', 'Data Lake'],
      ['/data-lineage', 'Data Lineage'],
    ])('opens %s as an operational workspace', async (path, title) => {
      const markup = await renderMarkup(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={[path]}>
            <Dashboard onSignOut={() => {}} />
          </MemoryRouter>
        </QueryClientProvider>,
      )

      expect(markup).toContain(`<h1>${title}`)
      expect(markup).not.toContain('This module is a non-operational preview')
    })
  })
})
