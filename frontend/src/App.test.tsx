import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import App from './App'

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('App', () => {
  // Routes are React.lazy, so the first paint is the Suspense fallback —
  // these must await the resolved chunk rather than assert synchronously.
  it('sends an unauthenticated visitor to the student login', async () => {
    render(<App />, { wrapper })
    expect(
      await screen.findByRole('heading', { name: /statics platform/i }),
    ).toBeInTheDocument()
    expect(await screen.findByText(/student portal/i)).toBeInTheDocument()
  })
})
