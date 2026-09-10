import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import AssignmentBuilder from './AssignmentBuilder'
import CourseDetailPage from './CourseDetailPage'
import { InstructorProvider } from '../context/InstructorContext'
import { server } from '../mocks/server'

const INSTRUCTOR = { id: 'i1', name: 'Prof. Marko', email: 'marko@university.edu' }
const BASE = 'http://localhost:8000/api/v1'
const COURSE_ID = '11111111-1111-4111-8111-111111111111'
const PUBLISHED = 'eeeeeee1-0000-4000-8000-000000000001' // 8 problems, audience all
const DRAFT = 'eeeeeee1-0000-4000-8000-000000000002' // 3 problems, selected

function renderAt(path: string) {
  server.use(
    http.get(`${BASE}/auth/instructor/me`, () =>
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
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/admin/assignments/:assignmentId" element={<AssignmentBuilder />} />
            <Route path="/admin/courses/:courseId" element={<CourseDetailPage />} />
            <Route path="/admin/login" element={<p>login</p>} />
          </Routes>
        </MemoryRouter>
      </InstructorProvider>
    </QueryClientProvider>,
  )
}

const openBuilder = (id = PUBLISHED) => renderAt(`/admin/assignments/${id}`)

/** Current values of every input carrying `label`, in document order. */
const valuesFor = (label: string) =>
  screen.getAllByLabelText<HTMLInputElement>(label).map((input) => input.value)

describe('assignment builder', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('loads an assignment with its settings and problem slots', async () => {
    openBuilder()
    expect(
      await screen.findByRole('heading', { name: /Truss Analysis — Fall 2026/ }),
    ).toBeInTheDocument()
    expect(screen.getByText('Published')).toBeInTheDocument()
    expect(await screen.findByText(/8 problems · 8 points total/)).toBeInTheDocument()
  })

  it('renders the difficulty form from the problem-type catalogue', async () => {
    openBuilder()
    await screen.findByText(/8 problems/)

    // Labels come from paramsSchema, not from anything hardcoded in admin/.
    expect(screen.getAllByLabelText('Joints').length).toBe(8)
    expect(screen.getAllByLabelText('Max load (kN)').length).toBe(8)
    expect(screen.getAllByLabelText('Applied loads').length).toBe(8)
  })

  it('renders whatever knobs the catalogue declares, including unknown ones', async () => {
    // Proves the form is data-driven: a param the UI has never heard of renders.
    server.use(
      http.get(`${BASE}/admin/problem-types`, () =>
        HttpResponse.json([
          {
            problemType: 'truss',
            displayName: 'Planar truss',
            paramsSchema: [
              {
                name: 'wobbliness',
                label: 'Wobbliness',
                valueType: 'integer',
                default: 2,
                minimum: 1,
                maximum: 9,
                step: 1,
                helpText: 'Invented for this test.',
              },
            ],
          },
        ]),
      ),
    )
    openBuilder()
    await screen.findByText(/8 problems/)

    expect(screen.getAllByLabelText('Wobbliness').length).toBe(8)
    expect(screen.queryByLabelText('Joints')).toBeNull()
  })

  it('renders a knob with a closed choice list as a labelled select', async () => {
    // Direction of loads is a set of choices, not a number an instructor should
    // have to look up — the catalogue says so and the form obeys, with no
    // problem-type knowledge in admin/.
    server.use(
      http.get(`${BASE}/admin/problem-types`, () =>
        HttpResponse.json([
          {
            problemType: 'truss',
            displayName: 'Planar truss',
            paramsSchema: [
              {
                name: 'load_direction',
                label: 'Force direction',
                valueType: 'integer',
                default: 0,
                minimum: 0,
                maximum: 3,
                step: 1,
                helpText: 'Restricts which cardinal directions point loads may take.',
                options: [
                  { value: 0, label: 'Any direction' },
                  { value: 1, label: 'Vertical only' },
                  { value: 2, label: 'Horizontal only' },
                  { value: 3, label: 'Downward only' },
                ],
              },
            ],
          },
        ]),
      ),
    )
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    const selects = screen.getAllByLabelText<HTMLSelectElement>('Force direction')
    expect(selects.length).toBe(3)
    expect(selects[0].tagName).toBe('SELECT')
    expect(
      within(selects[0]).getAllByRole('option').map((o) => o.textContent),
    ).toEqual(['Any direction', 'Vertical only', 'Horizontal only', 'Downward only'])

    // The numeric code, not the label, is what gets stored in the slot params.
    await user.selectOptions(selects[0], '3')
    expect(selects[0].value).toBe('3')
    expect(screen.getAllByLabelText<HTMLSelectElement>('Force direction')[1].value).toBe('0')
  })

  it('surfaces a stored choice value the catalogue no longer offers', async () => {
    // The ramp presets write joint counts into whichever knob the catalogue
    // lists first, which for a choice knob is out of range. A blank select
    // would silently save a value nobody picked.
    server.use(
      http.get(`${BASE}/admin/problem-types`, () =>
        HttpResponse.json([
          {
            problemType: 'truss',
            displayName: 'Planar truss',
            paramsSchema: [
              {
                name: 'support_case',
                label: 'Support Configuration',
                valueType: 'integer',
                default: 2,
                minimum: 1,
                maximum: 3,
                step: 1,
                helpText: 'Boundary conditions holding the body in equilibrium.',
                options: [
                  { value: 1, label: '3 Rollers' },
                  { value: 2, label: 'Pin + Roller' },
                  { value: 3, label: 'Fixed Cantilever Wall' },
                ],
              },
            ],
          },
        ]),
      ),
    )
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    await user.click(screen.getByRole('button', { name: /Standard \(8\)/ }))
    await screen.findByText(/8 problems/)

    const selects = screen.getAllByLabelText<HTMLSelectElement>('Support Configuration')
    // The ramp wrote 3,3,4,4,5,5,6,6 — 3 is a real choice, 4 upwards is not.
    expect(selects[0].value).toBe('3')
    expect(selects[2].value).toBe('4')
    expect(within(selects[2]).getByRole('option', { name: 'Unknown (4)' })).toBeInTheDocument()
  })

  it('applies a difficulty ramp preset', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    await user.click(screen.getByRole('button', { name: /Standard \(8\)/ }))

    expect(await screen.findByText(/8 problems/)).toBeInTheDocument()
    // The legacy [3,3,4,4,5,5,6,6] ramp.
    expect(valuesFor('Joints')).toEqual(['3', '3', '4', '4', '5', '5', '6', '6'])
  })

  it('warns about unsaved changes and clears the warning after saving', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    await user.click(screen.getByRole('button', { name: /Gentle \(6\)/ }))
    expect(await screen.findByText(/unsaved changes/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(screen.queryByText(/unsaved changes/i)).toBeNull()
    })
    expect(await screen.findByRole('button', { name: /^saved$/i })).toBeDisabled()
  })

  it('persists problem slots so a reopen shows the saved ramp', async () => {
    const user = userEvent.setup()
    const first = openBuilder(DRAFT)
    await screen.findByText(/3 problems/)
    await user.click(screen.getByRole('button', { name: /Gentle \(6\)/ }))
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    await screen.findByRole('button', { name: /^saved$/i })
    first.unmount()

    openBuilder(DRAFT)
    expect(await screen.findByText(/6 problems/)).toBeInTheDocument()
  })

  it('adds, reorders and removes a problem slot', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    await user.click(screen.getByRole('button', { name: /add problem/i }))
    expect(await screen.findByText(/4 problems/)).toBeInTheDocument()

    // Distinguish slot 1 from slot 2 before moving.
    const joints = screen.getAllByLabelText<HTMLInputElement>('Joints')
    await user.clear(joints[0])
    await user.type(joints[0], '7')

    await user.click(screen.getByRole('button', { name: /move problem 1 down/i }))
    expect(valuesFor('Joints')[1]).toBe('7')

    await user.click(screen.getByRole('button', { name: /remove problem 4/i }))
    expect(await screen.findByText(/3 problems/)).toBeInTheDocument()
  })

  it('refuses to publish an assignment with no problems', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    for (const label of ['remove problem 3', 'remove problem 2', 'remove problem 1']) {
      await user.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))
    }
    await screen.findByText(/no problems yet/i)

    // A published empty assignment is a dead end for the student.
    expect(screen.getByRole('button', { name: /^publish$/i })).toBeDisabled()
  })

  it('publishes a draft and reflects who can see it', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)
    expect(screen.getByText('Draft')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^publish$/i }))

    expect(await screen.findByText('Published')).toBeInTheDocument()
    expect(screen.getByText(/1 selected students/)).toBeInTheDocument()
  })

  it('switches targeting from everyone to specific students', async () => {
    const user = userEvent.setup()
    openBuilder()
    await screen.findByText(/8 problems/)

    await user.click(screen.getByRole('radio', { name: /specific students/i }))

    // Only assignable roster entries appear — dropped and declined are excluded.
    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.queryByText('Melba Roy')).toBeNull()
    expect(screen.queryByText('Dorothy Vaughan')).toBeNull()

    await user.click(screen.getByRole('button', { name: /select all/i }))
    expect(await screen.findByText(/of 5 selected/)).toBeInTheDocument()
  })

  it('marks unregistered students as targetable', async () => {
    const user = userEvent.setup()
    openBuilder()
    await screen.findByText(/8 problems/)
    await user.click(screen.getByRole('radio', { name: /specific students/i }))

    // Rostered ahead of signing up — still assignable, which is the point.
    const row = (await screen.findByText('Katherine Johnson')).closest('label')
    expect(row).not.toBeNull()
    if (row) expect(within(row).getByText('not registered')).toBeInTheDocument()
  })

  it('previews a problem using the shared renderer registry', async () => {
    const user = userEvent.setup()
    openBuilder()
    await screen.findByText(/8 problems/)

    const previews = screen.getAllByRole('button', { name: /^preview$/i })
    await user.click(previews[0])

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/problem 1 preview/i)).toBeInTheDocument()
    // The diagram is lazy-loaded through problems/registry.
    await waitFor(() => {
      expect(within(dialog).getByRole('img')).toBeInTheDocument()
    })

    await user.click(within(dialog).getByRole('button', { name: /close/i }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('rejects a slug that collides inside the same course', async () => {
    const user = userEvent.setup()
    openBuilder(DRAFT)
    await screen.findByText(/3 problems/)

    const slug = screen.getByLabelText(/url slug/i)
    await user.clear(slug)
    await user.type(slug, 'truss-fall-2026')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByText(/slug is already used/i)).toBeInTheDocument()
  })

  it('creates an assignment from the course page and lands in the builder', async () => {
    const user = userEvent.setup()
    renderAt(`/admin/courses/${COURSE_ID}`)
    await screen.findByRole('tab', { name: 'Assignments' })

    await user.click(screen.getByRole('tab', { name: 'Assignments' }))
    expect(await screen.findByText('Truss Analysis — Fall 2026')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /new assignment/i }))
    await user.type(screen.getByLabelText(/title/i), 'Homework 3 — Frames')
    // Slug is derived from the title until edited.
    expect(screen.getByLabelText(/url slug/i)).toHaveValue('homework-3-frames')

    await user.click(screen.getByRole('button', { name: /create and add problems/i }))

    // New assignments start empty, so the builder opens on the problems step.
    expect(await screen.findByText(/no problems yet/i)).toBeInTheDocument()
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  it('shows a not-found message for an unknown assignment', async () => {
    openBuilder('does-not-exist')
    expect(
      await screen.findByText(/does not exist, or you do not have access/i),
    ).toBeInTheDocument()
  })
})
