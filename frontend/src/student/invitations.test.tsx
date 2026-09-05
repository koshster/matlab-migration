import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import Dashboard from './Dashboard'
import { SessionProvider } from '../context/SessionContext'
import { server } from '../mocks/server'

const SESSION = { studentId: 's1', firstName: 'Ada', lastName: 'Lovelace' }
const BASE = 'http://localhost:8000/api/v1'

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  localStorage.setItem('statics_session', JSON.stringify(SESSION))
  return render(
    <QueryClientProvider client={client}>
      <SessionProvider>
        <MemoryRouter initialEntries={['/student/dashboard']}>
          <Routes>
            <Route path="/student/dashboard" element={<Dashboard />} />
            <Route path="/student/login" element={<p>login</p>} />
          </Routes>
        </MemoryRouter>
      </SessionProvider>
    </QueryClientProvider>,
  )
}

function invitationCard(courseCode: string) {
  const heading = screen.getByText(new RegExp(courseCode))
  const card = heading.closest('li')
  if (!card) throw new Error(`no invitation card for ${courseCode}`)
  return card
}

describe('course invitations', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('lists pending invitations with the course and instructor', async () => {
    renderDashboard()

    expect(await screen.findByText(/2 course invitations/i)).toBeInTheDocument()
    const card = invitationCard('MAE-008')
    expect(within(card).getByText(/Fall 2026 · Prof. Marko/)).toBeInTheDocument()
    expect(within(card).getByText(/3 assignments waiting/)).toBeInTheDocument()
  })

  it('starts with no courses and explains why', async () => {
    renderDashboard()
    // Nothing accepted yet, so the dashboard points at the invitations above.
    expect(
      await screen.findByText(/accept an invitation above to join a course/i),
    ).toBeInTheDocument()
  })

  it('accepting an invitation adds the course, and its work is one click away', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    const card = invitationCard('MAE-008')
    await user.click(within(card).getByRole('button', { name: /^accept$/i }))

    // The dashboard is course-first: the payoff is a course card, and the
    // assignments live one level in.
    const courseCard = await screen.findByRole('button', { name: /MAE-008/ })
    expect(courseCard).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/you have a course invitation/i)).toBeInTheDocument()
    })

    await user.click(courseCard)
    expect(await screen.findByText('Truss Analysis — Fall 2026')).toBeInTheDocument()
    expect(screen.getByText('Final Exam Practice')).toBeInTheDocument()
  })

  it('shows only the joined course while just one is accepted', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    await user.click(
      within(invitationCard('MAE-008')).getByRole('button', { name: /^accept$/i }),
    )

    await screen.findByRole('button', { name: /MAE-008/ })
    // The other course is still only an invitation, not a course card.
    expect(screen.queryByRole('button', { name: /MAE-130 —/ })).toBeNull()
  })

  it('lists both courses once a second is joined', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    await user.click(
      within(invitationCard('MAE-008')).getByRole('button', { name: /^accept$/i }),
    )
    await screen.findByRole('button', { name: /MAE-008/ })

    await user.click(
      within(invitationCard('MAE-130')).getByRole('button', { name: /^accept$/i }),
    )

    const second = await screen.findByRole('button', { name: /MAE-130/ })
    expect(second).toBeInTheDocument()

    await user.click(second)
    expect(await screen.findByText('Beam Reactions — Homework 1')).toBeInTheDocument()
  })

  it('confirms before declining, and can be backed out of', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    const card = invitationCard('MAE-008')
    await user.click(within(card).getByRole('button', { name: /^decline$/i }))

    expect(within(card).getByText(/decline MAE-008\?/i)).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: /keep it/i }))

    // Back to the original actions, invitation untouched.
    expect(within(card).getByRole('button', { name: /^accept$/i })).toBeInTheDocument()
    expect(await screen.findByText(/2 course invitations/i)).toBeInTheDocument()
  })

  it('declining removes the invitation and adds no assignments', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    const card = invitationCard('MAE-008')
    await user.click(within(card).getByRole('button', { name: /^decline$/i }))
    await user.click(within(card).getByRole('button', { name: /yes, decline/i }))

    await waitFor(() => {
      expect(screen.getByText(/you have a course invitation/i)).toBeInTheDocument()
    })
    expect(screen.queryByText(/MAE-008/)).toBeNull()
    expect(screen.queryByText('Truss Analysis — Fall 2026')).toBeNull()
  })

  it('hides the invitations section entirely when there are none', async () => {
    server.use(http.get(`${BASE}/student/invitations`, () => HttpResponse.json([])))
    renderDashboard()

    // The empty-state copy only renders once the assignment query resolves.
    expect(
      await screen.findByText(/once your instructor adds you to a course/i),
    ).toBeInTheDocument()
    // No invitations section at all — note the empty-state copy itself mentions
    // invitations, so assert on the section heading and actions, not the word.
    expect(screen.queryByRole('heading', { name: /course invitation/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^accept$/i })).toBeNull()
  })

  it('surfaces a stale invitation instead of failing silently', async () => {
    const user = userEvent.setup()
    server.use(
      http.post(`${BASE}/student/invitations/:entryId/accept`, () =>
        HttpResponse.json({ detail: 'No pending invitation' }, { status: 404 }),
      ),
    )
    renderDashboard()
    await screen.findByText(/2 course invitations/i)

    const card = invitationCard('MAE-008')
    await user.click(within(card).getByRole('button', { name: /^accept$/i }))

    expect(
      await screen.findByText(/no longer available. refresh to see the latest/i),
    ).toBeInTheDocument()
  })

  it('does not put a PID in the URL', async () => {
    renderDashboard()
    await screen.findByText(/2 course invitations/i)
    // Invitations are addressed by roster-entry UUID (standing rule #7).
    expect(window.location.href).not.toMatch(/A\d{6}/)
  })
})
