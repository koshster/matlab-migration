import { http, HttpResponse } from 'msw'
import assignmentSummary from '@statics/contract/fixtures/assignment-summary.json'
import truss3node from '@statics/contract/fixtures/truss-3node.json'
import truss4node from '@statics/contract/fixtures/truss-4node.json'
import truss6node from '@statics/contract/fixtures/truss-6node.json'
import checkCorrect from '@statics/contract/fixtures/check-correct.json'
import checkPartial from '@statics/contract/fixtures/check-partial.json'
import submissionResult from '@statics/contract/fixtures/submission-result.json'

const BASE = 'http://localhost:8000/api/v1'

// Rotate through fixture problems by index so all 8 problems render something
const problemByIndex = (index: number) => {
  if (index <= 2) return { ...truss3node, index }
  if (index <= 4) return { ...truss4node, index }
  if (index <= 6) return { ...truss6node, index }
  return { ...truss6node, index }
}

// Track check attempts per problem in memory (resets on page reload)
const checkCounts: Record<number, number> = {}

export const handlers = [
  // Student session — always succeeds in dev
  http.post(`${BASE}/auth/student/session`, () => {
    return HttpResponse.json({
      student: { id: 'mock-student-uuid', firstName: 'Demo', lastName: 'Student' },
      assignment: assignmentSummary,
    })
  }),

  // Assignment summary
  http.get(`${BASE}/assignments/:slug`, () => {
    return HttpResponse.json(assignmentSummary)
  }),

  // Problem by index
  http.get(`${BASE}/assignments/:slug/problems/:index`, ({ params }) => {
    const index = Number(params['index'])
    return HttpResponse.json(problemByIndex(index))
  }),

  // Save answers — always succeeds
  http.put(`${BASE}/assignments/:slug/problems/:index/answers`, () => {
    return HttpResponse.json({ savedAt: new Date().toISOString() })
  }),

  // Check answers — first attempt is partial, second is correct
  http.post(`${BASE}/assignments/:slug/problems/:index/check`, ({ params }) => {
    const index = Number(params['index'])
    checkCounts[index] = (checkCounts[index] ?? 0) + 1
    const result = checkCounts[index] >= 2 ? checkCorrect : checkPartial
    return HttpResponse.json({ ...result, attemptCount: checkCounts[index] })
  }),

  // Submit
  http.post(`${BASE}/assignments/:slug/submit`, () => {
    return HttpResponse.json(submissionResult)
  }),

  // Result (after submit)
  http.get(`${BASE}/assignments/:slug/result`, () => {
    return HttpResponse.json(submissionResult)
  }),

  // Instructor login — any password works in dev
  http.post(`${BASE}/auth/instructor/login`, async ({ request }) => {
    const body = await request.json() as { email?: string }
    return HttpResponse.json({
      instructor: {
        id: 'mock-instructor-uuid',
        email: body.email ?? 'marko@university.edu',
        name: 'Prof. Marko',
      },
    })
  }),

  // Instructor register — 409 if email contains "taken"
  http.post(`${BASE}/auth/instructor/register`, async ({ request }) => {
    const body = await request.json() as { name?: string; email?: string }
    if (body.email?.includes('taken')) {
      return HttpResponse.json({ detail: 'Email already registered' }, { status: 409 })
    }
    return HttpResponse.json(
      {
        instructor: {
          id: 'mock-instructor-uuid',
          email: body.email ?? 'new@university.edu',
          name: body.name ?? 'New Instructor',
        },
      },
      { status: 201 },
    )
  }),

  // Instructor logout
  http.post(`${BASE}/auth/instructor/logout`, () => {
    return HttpResponse.json({ ok: true })
  }),

  // Student login — any password works; 401 if pid === 'invalid'
  http.post(`${BASE}/auth/student/login`, async ({ request }) => {
    const body = await request.json() as { pid?: string }
    if (body.pid === 'invalid') {
      return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
    }
    return HttpResponse.json({
      student: { id: 'mock-student-uuid', firstName: 'Demo', lastName: 'Student' },
    })
  }),

  // Student register — 409 if pid contains 'taken'
  http.post(`${BASE}/auth/student/register`, async ({ request }) => {
    const body = await request.json() as { pid?: string; firstName?: string; lastName?: string }
    if (body.pid?.includes('taken')) {
      return HttpResponse.json({ detail: 'PID already registered' }, { status: 409 })
    }
    return HttpResponse.json(
      {
        student: {
          id: 'mock-student-uuid',
          firstName: body.firstName ?? 'Demo',
          lastName: body.lastName ?? 'Student',
        },
      },
      { status: 201 },
    )
  }),

  // Student assignment list (dashboard) — three assignments across all status states
  http.get(`${BASE}/student/assignments`, () => {
    return HttpResponse.json([
      {
        slug: 'truss-fall-2026',
        title: 'Truss Analysis — Fall 2026',
        status: 'in_progress',
        score: null,
        dueAt: '2026-12-15T23:59:00Z',
        problemCount: 8,
      },
      {
        slug: 'truss-quiz-week8',
        title: 'Truss Review Quiz — Week 8',
        status: 'not_started',
        score: null,
        dueAt: '2026-10-30T23:59:00Z',
        problemCount: 8,
      },
      {
        slug: 'truss-practice-final',
        title: 'Final Exam Practice',
        status: 'submitted',
        score: { earned: 6, total: 8 },
        dueAt: null,
        problemCount: 8,
      },
    ])
  }),
]
