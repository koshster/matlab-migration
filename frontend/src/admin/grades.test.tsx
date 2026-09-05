import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import CourseDetailPage from './CourseDetailPage'
import { InstructorProvider } from '../context/InstructorContext'
import { server } from '../mocks/server'

const INSTRUCTOR = { id: 'i1', name: 'Prof. Marko', email: 'marko@university.edu' }
const COURSE_ID = '11111111-1111-4111-8111-111111111111'

function renderGrades() {
  server.use(
    http.get('http://localhost:8000/api/v1/auth/instructor/me', () =>
      HttpResponse.json({ instructor: INSTRUCTOR }),
    ),
  )
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

async function openGradesTab() {
  const user = userEvent.setup()
  renderGrades()
  await user.click(await screen.findByRole('tab', { name: 'Grades' }))
  return user
}

describe('instructor grades tab', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('shows class summary statistics', async () => {
    await openGradesTab()

    expect(await screen.findByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Average')).toBeInTheDocument()
    // 1 of 3 students has final work; the average is over that one.
    expect(screen.getByText('over 1 graded')).toBeInTheDocument()
  })

  it('lists every roster student, including one who never started', async () => {
    await openGradesTab()

    expect(await screen.findByText('Alice Chen')).toBeInTheDocument()
    expect(screen.getByText('Bob Torres')).toBeInTheDocument()
    // The point of a roster-driven denominator: absence is visible.
    expect(screen.getByText('Carol Kim')).toBeInTheDocument()
    expect(screen.getByText('Not started')).toBeInTheDocument()
  })

  it('withholds a score until the student’s work is final', async () => {
    await openGradesTab()

    const alice = (await screen.findByText('Alice Chen')).closest('tr')
    const bob = screen.getByText('Bob Torres').closest('tr')
    if (!alice || !bob) throw new Error('expected a row per student')

    expect(within(alice).getByText('3 / 3')).toBeInTheDocument()
    // Bob is mid-assignment: showing a partial score as a grade would
    // misrepresent him.
    expect(within(bob).getByText('—')).toBeInTheDocument()
  })

  it('filters the roster by status', async () => {
    const user = await openGradesTab()
    await screen.findByText('Alice Chen')

    await user.click(screen.getByRole('button', { name: /^Not started \(1\)$/ }))

    expect(screen.getByText('Carol Kim')).toBeInTheDocument()
    expect(screen.queryByText('Alice Chen')).toBeNull()
  })

  it('searches by name or student id', async () => {
    const user = await openGradesTab()
    await screen.findByText('Alice Chen')

    await user.type(screen.getByLabelText('Search students'), 'A22222222')

    expect(screen.getByText('Bob Torres')).toBeInTheDocument()
    expect(screen.queryByText('Alice Chen')).toBeNull()
  })

  it('shows per-problem success rates', async () => {
    await openGradesTab()

    expect(await screen.findByText('Success rate by problem')).toBeInTheDocument()
    // Problem 2: one of two students who attempted it got it right.
    expect(screen.getByText('50% of 2')).toBeInTheDocument()
  })
})
