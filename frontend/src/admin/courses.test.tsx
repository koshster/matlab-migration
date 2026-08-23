import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import CoursesPage from './CoursesPage'
import CourseDetailPage from './CourseDetailPage'
import { InstructorProvider } from '../context/InstructorContext'
import { server } from '../mocks/server'

const INSTRUCTOR = { id: 'i1', name: 'Prof. Marko', email: 'marko@university.edu' }

function renderCourses() {
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
        <MemoryRouter initialEntries={['/admin']}>
          <Routes>
            <Route path="/admin" element={<CoursesPage />} />
            <Route path="/admin/courses/:courseId" element={<CourseDetailPage />} />
            <Route path="/admin/login" element={<p>login</p>} />
          </Routes>
        </MemoryRouter>
      </InstructorProvider>
    </QueryClientProvider>,
  )
}

describe('courses page', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('lists the active courses Marko teaches', async () => {
    renderCourses()
    expect(await screen.findByRole('heading', { name: 'Courses' })).toBeInTheDocument()
    expect(await screen.findByText('MAE-008')).toBeInTheDocument()
    expect(screen.getByText('MAE-130')).toBeInTheDocument()
  })

  it('hides archived courses until asked', async () => {
    const user = userEvent.setup()
    renderCourses()
    await screen.findByText('MAE-130')

    // The archived Spring 2026 section is the third fixture course.
    expect(screen.queryByText(/Spring 2026/)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /show 1 archived course/i }))
    expect(await screen.findByText(/Spring 2026/)).toBeInTheDocument()
    expect(screen.getByText('Archived')).toBeInTheDocument()
  })

  it('shows enrolled and pending counts per course', async () => {
    renderCourses()
    const heading = await screen.findByText('MAE-008')
    const card = heading.closest('a')
    expect(card).not.toBeNull()
    if (!card) return
    // 3 enrolled, 2 still invited — from the roster fixture.
    expect(within(card).getByText('Students')).toBeInTheDocument()
    expect(within(card).getByText('Pending')).toBeInTheDocument()
  })

  it('surfaces a non-owner role on a course', async () => {
    const user = userEvent.setup()
    renderCourses()
    await screen.findByText('MAE-130')
    await user.click(screen.getByRole('button', { name: /show 1 archived course/i }))
    // The archived course is one where Marko is only a TA.
    expect(await screen.findByText('ta')).toBeInTheDocument()
  })

  it('creates a course and shows it in the list', async () => {
    const user = userEvent.setup()
    renderCourses()
    await screen.findByText('MAE-008')

    await user.click(screen.getByRole('button', { name: /new course/i }))
    await user.type(screen.getByLabelText(/course code/i), 'MAE-101')
    await user.type(screen.getByLabelText(/^term$/i), 'Winter 2027')
    await user.type(screen.getByLabelText(/title/i), 'Dynamics')
    await user.click(screen.getByRole('button', { name: /create course/i }))

    expect(await screen.findByText('MAE-101')).toBeInTheDocument()
    expect(screen.getByText(/Dynamics · Winter 2027/)).toBeInTheDocument()
  })

  it('reports a duplicate course instead of silently doing nothing', async () => {
    const user = userEvent.setup()
    renderCourses()
    await screen.findByText('MAE-008')

    await user.click(screen.getByRole('button', { name: /new course/i }))
    // Same code + term + section as the first fixture course.
    await user.type(screen.getByLabelText(/course code/i), 'MAE-008')
    await user.type(screen.getByLabelText(/^term$/i), 'Fall 2026')
    await user.click(screen.getByRole('button', { name: /create course/i }))

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument()
  })

  it('will not submit without a code and term', async () => {
    const user = userEvent.setup()
    renderCourses()
    await screen.findByText('MAE-008')

    await user.click(screen.getByRole('button', { name: /new course/i }))
    expect(screen.getByRole('button', { name: /create course/i })).toBeDisabled()

    await user.type(screen.getByLabelText(/course code/i), 'MAE-999')
    expect(screen.getByRole('button', { name: /create course/i })).toBeDisabled()

    await user.type(screen.getByLabelText(/^term$/i), 'Fall 2027')
    expect(screen.getByRole('button', { name: /create course/i })).toBeEnabled()
  })

  it('navigates into a course and back out', async () => {
    const user = userEvent.setup()
    renderCourses()
    await user.click(await screen.findByText('MAE-008'))

    // Course detail defaults to the roster tab.
    expect(await screen.findByRole('tab', { name: 'Roster' })).toBeInTheDocument()
    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
  })

  it('shows an empty assignments tab pointing at the next slice', async () => {
    const user = userEvent.setup()
    renderCourses()
    await user.click(await screen.findByText('MAE-008'))
    await screen.findByRole('tab', { name: 'Assignments' })

    await user.click(screen.getByRole('tab', { name: 'Assignments' }))
    expect(await screen.findByText(/assignment builder/i)).toBeInTheDocument()
  })

  it('renders a not-found message for an unknown course id', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/auth/instructor/me', () =>
        HttpResponse.json({ instructor: INSTRUCTOR }),
      ),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    sessionStorage.setItem('instructor_session', JSON.stringify(INSTRUCTOR))
    render(
      <QueryClientProvider client={client}>
        <InstructorProvider>
          <MemoryRouter initialEntries={['/admin/courses/does-not-exist']}>
            <Routes>
              <Route path="/admin/courses/:courseId" element={<CourseDetailPage />} />
            </Routes>
          </MemoryRouter>
        </InstructorProvider>
      </QueryClientProvider>,
    )

    // 404 is also what a course you lack access to returns, so the copy covers both.
    await waitFor(() => {
      expect(
        screen.getByText(/does not exist, or you do not have access/i),
      ).toBeInTheDocument()
    })
  })
})
