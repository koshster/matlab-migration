import { http, HttpResponse } from 'msw'
import type { components } from '@statics/contract/src/index'
import studentInvitations from '@statics/contract/fixtures/student-invitations.json'

type StudentInvitation = components['schemas']['StudentInvitation']
type StudentCourseSummary = components['schemas']['StudentCourseSummary']
type StudentAssignmentListItem = components['schemas']['StudentAssignmentListItem']

const BASE = 'http://localhost:8000/api/v1'

const MAE008 = {
  id: '11111111-1111-4111-8111-111111111111',
  code: 'MAE-008',
  term: 'Fall 2026',
  title: 'Statics',
}
const MAE130 = {
  id: '22222222-2222-4222-8222-222222222222',
  code: 'MAE-130',
  term: 'Fall 2026',
  title: 'Mechanics of Materials',
}

// Assignments are keyed by course so accepting an invitation visibly adds work
// and declining leaves the dashboard untouched.
const ASSIGNMENTS_BY_COURSE: Record<string, StudentAssignmentListItem[]> = {
  [MAE008.id]: [
    {
      slug: 'truss-fall-2026',
      title: 'Truss Analysis — Fall 2026',
      status: 'in_progress',
      score: null,
      dueAt: '2026-12-15T23:59:00Z',
      problemCount: 8,
      course: MAE008,
    },
    {
      slug: 'truss-quiz-week8',
      title: 'Truss Review Quiz — Week 8',
      status: 'not_started',
      score: null,
      dueAt: '2026-10-30T23:59:00Z',
      problemCount: 8,
      course: MAE008,
    },
    {
      slug: 'truss-practice-final',
      title: 'Final Exam Practice',
      status: 'submitted',
      score: { earned: 6, total: 8 },
      dueAt: null,
      problemCount: 8,
      course: MAE008,
    },
  ],
  [MAE130.id]: [
    {
      slug: 'beam-intro-hw1',
      title: 'Beam Reactions — Homework 1',
      status: 'not_started',
      score: null,
      dueAt: '2026-11-05T23:59:00Z',
      problemCount: 6,
      course: MAE130,
    },
  ],
}

// Mutable session state: which invitations are still pending, and which courses
// the student has joined. Starts with both fixture invitations pending and
// nothing joined, so the accept flow is what puts assignments on the dashboard.
let pending: StudentInvitation[] = structuredClone(studentInvitations)
const joined = new Map<string, StudentCourseSummary>()

/**
 * Restore the starting state. Module state persists across tests in a file, so
 * a test that accepts an invitation would otherwise change what later tests see.
 */
export function resetStudentMockState(): void {
  pending = structuredClone(studentInvitations)
  joined.clear()
}

function courseSummary(inv: StudentInvitation): StudentCourseSummary {
  return {
    id: inv.course.id,
    code: inv.course.code,
    term: inv.course.term,
    section: '001',
    title: inv.course.title,
    instructorName: inv.instructorName,
    assignmentCount: inv.assignmentCount,
    enrolledAt: new Date().toISOString(),
  }
}

export const studentHandlers = [
  http.get(`${BASE}/student/invitations`, () => HttpResponse.json(pending)),

  http.post(`${BASE}/student/invitations/:entryId/accept`, ({ params }) => {
    const entryId = String(params['entryId'])
    const invitation = pending.find((i) => i.id === entryId)
    if (!invitation) {
      // Already accepted is idempotent; anything else is genuinely unknown.
      const already = [...joined.values()].find((c) => c.id === entryId)
      if (already) return HttpResponse.json(already)
      return HttpResponse.json({ detail: 'No pending invitation' }, { status: 404 })
    }
    pending = pending.filter((i) => i.id !== entryId)
    const course = courseSummary(invitation)
    joined.set(course.id, course)
    return HttpResponse.json(course)
  }),

  http.post(`${BASE}/student/invitations/:entryId/decline`, ({ params }) => {
    const entryId = String(params['entryId'])
    if (!pending.some((i) => i.id === entryId)) {
      return HttpResponse.json({ detail: 'No pending invitation' }, { status: 404 })
    }
    pending = pending.filter((i) => i.id !== entryId)
    return HttpResponse.json({ ok: true })
  }),

  http.get(`${BASE}/student/courses`, () => HttpResponse.json([...joined.values()])),

  // Overrides the assignment list in handlers.ts: only courses the student has
  // actually joined contribute assignments.
  http.get(`${BASE}/student/assignments`, () => {
    const items = [...joined.keys()].flatMap((id) => ASSIGNMENTS_BY_COURSE[id] ?? [])
    return HttpResponse.json(items)
  }),
]
