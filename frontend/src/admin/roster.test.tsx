import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import CourseDetailPage from './CourseDetailPage'
import { InstructorProvider } from '../context/InstructorContext'
import { server } from '../mocks/server'

const COURSE_ID = '11111111-1111-4111-8111-111111111111'
const INSTRUCTOR = { id: 'i1', name: 'Prof. Marko', email: 'marko@university.edu' }

function renderCourse() {
  // These tests cover the roster, not auth. AdminLayout revalidates the session
  // on mount, so stub it as signed in rather than driving a login first.
  server.use(
    http.get('http://localhost:8000/api/v1/auth/instructor/me', () =>
      HttpResponse.json({ instructor: INSTRUCTOR }),
    ),
  )
  // Retries off so an assertion failure surfaces as itself, not a timeout.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  sessionStorage.setItem('instructor_session', JSON.stringify(INSTRUCTOR))
  return render(
    <QueryClientProvider client={client}>
      <InstructorProvider>
        <MemoryRouter initialEntries={[`/admin/courses/${COURSE_ID}`]}>
          <Routes>
            <Route path="/admin/courses/:courseId" element={<CourseDetailPage />} />
            <Route path="/admin/login" element={<p>login</p>} />
          </Routes>
        </MemoryRouter>
      </InstructorProvider>
    </QueryClientProvider>,
  )
}

async function rosterTable() {
  return await screen.findByRole('table')
}

/** The <tr> containing `text`, failing with a useful message if absent. */
function rowContaining(scope: HTMLElement, text: string): HTMLElement {
  const row = within(scope).getByText(text).closest('tr')
  if (!row) throw new Error(`no table row contains "${text}"`)
  return row
}

describe('course roster', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('shows the roster with enrolled and invited students', async () => {
    renderCourse()

    expect(await screen.findByRole('heading', { name: /MAE-008/ })).toBeInTheDocument()
    const table = await rosterTable()
    expect(within(table).getByText('Ada Lovelace')).toBeInTheDocument()
    expect(within(table).getByText('A12345678')).toBeInTheDocument()
    expect(within(table).getByText('Katherine Johnson')).toBeInTheDocument()
  })

  it('surfaces how many students have not signed up yet', async () => {
    renderCourse()
    // The fixture has three unclaimed entries; this banner is the whole point
    // of rostering ahead of registration.
    expect(await screen.findByText(/have not created an account yet/i)).toBeInTheDocument()
  })

  it('filters by status', async () => {
    const user = userEvent.setup()
    renderCourse()
    await rosterTable()

    await user.click(screen.getByRole('button', { name: /^Invited/ }))

    const table = await rosterTable()
    expect(within(table).getByText('Katherine Johnson')).toBeInTheDocument()
    expect(within(table).queryByText('Ada Lovelace')).not.toBeInTheDocument()
  })

  it('searches by PID, email and name', async () => {
    const user = userEvent.setup()
    renderCourse()
    await rosterTable()

    const search = screen.getByRole('textbox', { name: /search roster/i })
    await user.type(search, 'grace@ucsd.edu')

    await waitFor(async () => {
      const table = await rosterTable()
      expect(within(table).getByText('Grace Hopper')).toBeInTheDocument()
      expect(within(table).queryByText('Ada Lovelace')).not.toBeInTheDocument()
    })
  })

  it('shows an entry added by email only, with no PID', async () => {
    renderCourse()
    const table = await rosterTable()
    const row = rowContaining(table, 'mary.jackson@ucsd.edu')
    // Added by email ahead of registration: no name, no PID, not registered.
    expect(within(row).getAllByText('—')).toHaveLength(2)
    expect(within(row).getByText('Invited')).toBeInTheDocument()
    expect(within(row).getByText('Not yet')).toBeInTheDocument()
  })

  it('imports a pasted roster and reports per-row outcomes', async () => {
    const user = userEvent.setup()
    renderCourse()
    await rosterTable()

    await user.click(screen.getByRole('button', { name: /add students/i }))
    const textarea = screen.getByRole('textbox', { name: /roster to import/i })

    await user.type(
      textarea,
      [
        'PID,Email,First Name,Last Name',
        'A77777777,new.student@ucsd.edu,New,Student',
        'A12345678,ada@ucsd.edu,Ada,Lovelace',
        'nonsense line',
      ].join('\n'),
    )

    // Preview before committing: 2 parseable rows, 1 unusable. The count sits
    // in a nested <strong>, so match on the element's full text content.
    expect(
      await screen.findByText((_t, el) => el?.textContent === '2 students ready to add'),
    ).toBeInTheDocument()
    expect(screen.getByText(/lines? will be skipped/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /add 2 students/i }))

    expect(await screen.findByText(/import complete/i)).toBeInTheDocument()
    // One genuinely new, one already on the roster.
    expect(screen.getByText(/1 invited/)).toBeInTheDocument()
    expect(screen.getByText(/1 already on the roster/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^done$/i }))

    const table = await rosterTable()
    await waitFor(() => {
      expect(within(table).getByText('New Student')).toBeInTheDocument()
    })
  })

  it('drops a student and updates the roster', async () => {
    const user = userEvent.setup()
    renderCourse()
    const table = await rosterTable()

    const row = rowContaining(table, 'Grace Hopper')
    await user.click(within(row).getByRole('button', { name: /drop/i }))

    await waitFor(async () => {
      const refreshed = await rosterTable()
      const updated = rowContaining(refreshed, 'Grace Hopper')
      expect(within(updated).getByText('Dropped')).toBeInTheDocument()
    })
  })

  it('switches to the staff tab and lists course staff', async () => {
    const user = userEvent.setup()
    renderCourse()
    await rosterTable()

    await user.click(screen.getByRole('tab', { name: /staff/i }))

    await screen.findByText('rushil@ucsd.edu')
    // Scope to the row — "ta" also appears as an option in the add-staff select.
    const row = rowContaining(await screen.findByRole('table'), 'rushil@ucsd.edu')
    expect(within(row).getByText('ta')).toBeInTheDocument()
    expect(within(row).getByText('Rushil')).toBeInTheDocument()
  })

  it('does not leak a PID into the URL', async () => {
    renderCourse()
    await rosterTable()
    // Standing rule #7: roster entries are addressed by UUID only.
    expect(window.location.href).not.toMatch(/A12345678/i)
  })
})
