import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Dashboard from './Dashboard'

describe('Overview', () => {
  it('opens the database-backed view and makes the CSV view available', () => {
    const markup = renderToStaticMarkup(
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
    it('shows source registration without requiring sign-in', () => {
      const markup = renderToStaticMarkup(
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
  })
})
