import { http, HttpResponse } from 'msw'
import type { components } from '@statics/contract/src/index'
import adminCourses from '@statics/contract/fixtures/admin-courses.json'
import adminRoster from '@statics/contract/fixtures/admin-roster.json'
import adminStaff from '@statics/contract/fixtures/admin-staff.json'

type CourseSummary = components['schemas']['CourseSummary']
type RosterEntry = components['schemas']['RosterEntry']
type CourseStaffMember = components['schemas']['CourseStaffMember']
type RosterImportEntry = components['schemas']['RosterImportEntry']
type RosterImportRowResult = components['schemas']['RosterImportRowResult']

const BASE = 'http://localhost:8000/api/v1'

// Mutable in-memory state so the UI behaves like a real backend within a
// session: adding to the roster, dropping a student, and the derived counts on
// the course list all persist until reload.
let courses: CourseSummary[] = structuredClone(adminCourses) as CourseSummary[]
const rosterByCourse = new Map<string, RosterEntry[]>([
  [courses[0].id, structuredClone(adminRoster) as RosterEntry[]],
  [
    courses[1].id,
    [
      {
        id: 'aaaaaaa2-0000-4000-8000-000000000001',
        status: 'active',
        pid: 'A98765432',
        email: 'alan@ucsd.edu',
        firstName: 'Alan',
        lastName: 'Turing',
        hasAccount: true,
        invitedAt: '2026-08-03T10:00:00Z',
        acceptedAt: '2026-08-03T18:22:00Z',
      },
    ],
  ],
  [courses[2].id, []],
])
const staffByCourse = new Map<string, CourseStaffMember[]>([
  [courses[0].id, structuredClone(adminStaff) as CourseStaffMember[]],
  [courses[1].id, [structuredClone(adminStaff)[0]] as CourseStaffMember[]],
  [courses[2].id, structuredClone(adminStaff) as CourseStaffMember[]],
])

const SECOND_COURSE_ROSTER: RosterEntry[] = [
  {
    id: 'aaaaaaa2-0000-4000-8000-000000000001',
    status: 'active',
    pid: 'A98765432',
    email: 'alan@ucsd.edu',
    firstName: 'Alan',
    lastName: 'Turing',
    hasAccount: true,
    invitedAt: '2026-08-03T10:00:00Z',
    acceptedAt: '2026-08-03T18:22:00Z',
  },
]

/**
 * Restore the starting state. Module state persists across tests in a file, so
 * a test that drops a student or imports a roster would otherwise change what
 * later tests see.
 */
export function resetAdminMockState(): void {
  courses = structuredClone(adminCourses) as CourseSummary[]
  rosterByCourse.clear()
  rosterByCourse.set(courses[0].id, structuredClone(adminRoster) as RosterEntry[])
  rosterByCourse.set(courses[1].id, structuredClone(SECOND_COURSE_ROSTER))
  rosterByCourse.set(courses[2].id, [])
  staffByCourse.clear()
  staffByCourse.set(courses[0].id, structuredClone(adminStaff) as CourseStaffMember[])
  staffByCourse.set(courses[1].id, [structuredClone(adminStaff)[0]] as CourseStaffMember[])
  staffByCourse.set(courses[2].id, structuredClone(adminStaff) as CourseStaffMember[])
}

let idCounter = 1000
const nextId = (prefix: string) => `${prefix}-0000-4000-8000-${String(idCounter++).padStart(12, '0')}`

const notFound = () => HttpResponse.json({ detail: 'Course not found' }, { status: 404 })

function recount(courseId: string) {
  const course = courses.find((c) => c.id === courseId)
  const roster = rosterByCourse.get(courseId)
  if (!course || !roster) return
  course.studentCount = roster.filter((e) => e.status === 'active').length
  course.pendingInviteCount = roster.filter((e) => e.status === 'invited').length
}

function looksLikeEmail(value: string): boolean {
  if (!value || /\s/.test(value)) return false
  const at = value.lastIndexOf('@')
  if (at <= 0 || at === value.length - 1) return false
  const domain = value.slice(at + 1)
  return domain.includes('.') && !domain.startsWith('.') && !domain.endsWith('.')
}

export const adminHandlers = [
  http.get(`${BASE}/admin/courses`, () => HttpResponse.json(courses)),

  http.post(`${BASE}/admin/courses`, async ({ request }) => {
    const body = (await request.json()) as {
      code?: string
      term?: string
      section?: string
      title?: string
    }
    const code = body.code?.trim() ?? ''
    const term = body.term?.trim() ?? ''
    const section = body.section?.trim() || '001'

    const clash = courses.some(
      (c) => c.code === code && c.term === term && c.section === section,
    )
    if (clash) {
      return HttpResponse.json(
        { detail: 'A course with that code, term and section already exists' },
        { status: 409 },
      )
    }

    const course: CourseSummary = {
      id: nextId('dddddddd'),
      code,
      term,
      section,
      title: body.title?.trim() ?? '',
      isArchived: false,
      studentCount: 0,
      pendingInviteCount: 0,
      assignmentCount: 0,
      viewerRole: 'owner',
    }
    courses.unshift(course)
    rosterByCourse.set(course.id, [])
    staffByCourse.set(course.id, [structuredClone(adminStaff)[0]] as CourseStaffMember[])
    return HttpResponse.json(course, { status: 201 })
  }),

  http.get(`${BASE}/admin/courses/:courseId`, ({ params }) => {
    const course = courses.find((c) => c.id === params['courseId'])
    return course ? HttpResponse.json(course) : notFound()
  }),

  http.patch(`${BASE}/admin/courses/:courseId`, async ({ params, request }) => {
    const course = courses.find((c) => c.id === params['courseId'])
    if (!course) return notFound()
    const body = (await request.json()) as { title?: string; isArchived?: boolean }
    if (body.title !== undefined) course.title = body.title
    if (body.isArchived !== undefined) course.isArchived = body.isArchived
    return HttpResponse.json(course)
  }),

  http.get(`${BASE}/admin/courses/:courseId/roster`, ({ params }) => {
    const roster = rosterByCourse.get(String(params['courseId']))
    return roster ? HttpResponse.json(roster) : notFound()
  }),

  http.post(`${BASE}/admin/courses/:courseId/roster`, async ({ params, request }) => {
    const courseId = String(params['courseId'])
    const roster = rosterByCourse.get(courseId)
    if (!roster) return notFound()

    const body = (await request.json()) as { entries?: RosterImportEntry[] }
    const entries = body.entries ?? []
    const results: RosterImportRowResult[] = []

    entries.forEach((raw, i) => {
      const pid = raw.pid?.trim().toUpperCase() || null
      const email = raw.email?.trim().toLowerCase() || null
      const row = i + 1

      if (!pid && !email) {
        results.push({
          row,
          outcome: 'invalid',
          pid,
          email,
          message: 'needs a PID or an email',
        })
        return
      }
      if (email && !looksLikeEmail(email)) {
        results.push({ row, outcome: 'invalid', pid, email, message: 'malformed email' })
        return
      }

      const existing = roster.find(
        (e) => (pid && e.pid === pid) || (email && e.email === email),
      )
      if (existing) {
        results.push({ row, outcome: 'already_present', pid, email, message: null })
        return
      }

      // Stand-in for the claim step: a PID the mock "knows" already has an
      // account, so the entry links immediately instead of staying unclaimed.
      const knownAccount = pid ? pid.startsWith('DEMO') : false

      roster.push({
        id: nextId('aaaaaaa9'),
        status: 'invited',
        pid,
        email,
        firstName: raw.firstName?.trim() || null,
        lastName: raw.lastName?.trim() || null,
        hasAccount: knownAccount,
        invitedAt: new Date().toISOString(),
        acceptedAt: null,
      })
      results.push({
        row,
        outcome: knownAccount ? 'linked_existing_account' : 'added',
        pid,
        email,
        message: null,
      })
    })

    recount(courseId)

    return HttpResponse.json({
      added: results.filter((r) => r.outcome === 'added').length,
      alreadyPresent: results.filter((r) => r.outcome === 'already_present').length,
      linked: results.filter((r) => r.outcome === 'linked_existing_account').length,
      invalid: results.filter((r) => r.outcome === 'invalid').length,
      results,
    })
  }),

  http.patch(
    `${BASE}/admin/courses/:courseId/roster/:entryId`,
    async ({ params, request }) => {
      const courseId = String(params['courseId'])
      const roster = rosterByCourse.get(courseId)
      if (!roster) return notFound()
      const entry = roster.find((e) => e.id === params['entryId'])
      if (!entry) {
        return HttpResponse.json({ detail: 'Roster entry not found' }, { status: 404 })
      }
      const body = (await request.json()) as { status?: RosterEntry['status'] }
      if (body.status) entry.status = body.status
      recount(courseId)
      return HttpResponse.json(entry)
    },
  ),

  http.get(`${BASE}/admin/courses/:courseId/staff`, ({ params }) => {
    const staff = staffByCourse.get(String(params['courseId']))
    return staff ? HttpResponse.json(staff) : notFound()
  }),

  http.post(`${BASE}/admin/courses/:courseId/staff`, async ({ params, request }) => {
    const staff = staffByCourse.get(String(params['courseId']))
    if (!staff) return notFound()
    const body = (await request.json()) as { email?: string; role?: CourseStaffMember['role'] }
    const email = body.email?.trim().toLowerCase() ?? ''

    if (email.includes('unknown')) {
      return HttpResponse.json(
        { detail: 'No instructor with that email' },
        { status: 404 },
      )
    }
    if (staff.some((m) => m.email === email)) {
      return HttpResponse.json(
        { detail: 'That instructor already has a role on the course' },
        { status: 409 },
      )
    }

    const member: CourseStaffMember = {
      id: nextId('bbbbbbb9'),
      instructorId: nextId('cccccccc'),
      name: email.split('@')[0] ?? email,
      email,
      role: body.role ?? 'ta',
    }
    staff.push(member)
    return HttpResponse.json(member, { status: 201 })
  }),
]
