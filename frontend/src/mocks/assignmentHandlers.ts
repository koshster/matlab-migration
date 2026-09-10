import { http, HttpResponse } from 'msw'
import type { components } from '@statics/contract/src/index'
import truss3node from '@statics/contract/fixtures/truss-3node.json'
import truss4node from '@statics/contract/fixtures/truss-4node.json'
import truss6node from '@statics/contract/fixtures/truss-6node.json'

type AdminAssignmentDetail = components['schemas']['AdminAssignmentDetail']
type AdminProblemSlot = components['schemas']['AdminProblemSlot']
type ProblemTypeInfo = components['schemas']['ProblemTypeInfo']

const BASE = 'http://localhost:8000/api/v1'

const MAE008 = '11111111-1111-4111-8111-111111111111'
const MAE130 = '22222222-2222-4222-8222-222222222222'

/**
 * Mirrors what GET /admin/problem-types returns from the generator registry.
 * The builder renders its difficulty form from this, so adding a problem type
 * needs no admin UI change.
 */
const PROBLEM_TYPES: ProblemTypeInfo[] = [
  {
    problemType: 'truss',
    displayName: 'Planar truss',
    paramsSchema: [
      {
        name: 'num_nodes',
        label: 'Joints',
        valueType: 'integer',
        default: 3,
        minimum: 3,
        maximum: 8,
        step: 1,
        helpText: 'Members scale as 2n−3, so joints drive the problem’s size.',
      },
      {
        name: 'max_force',
        label: 'Max load (kN)',
        valueType: 'integer',
        default: 5,
        minimum: 1,
        maximum: 20,
        step: 1,
        helpText: 'Load magnitudes are whole numbers from 1 to this value.',
      },
      {
        name: 'load_count',
        label: 'Applied loads',
        valueType: 'integer',
        default: 1,
        minimum: 1,
        maximum: 2,
        step: 1,
        helpText: 'Clamped to the number of free joints on small trusses.',
      },
    ],
  },
  {
    problemType: 'rigid_body',
    displayName: '2D Rigid Body Equilibrium',
    paramsSchema: [
      {
        name: 'support_case',
        label: 'Support Configuration',
        valueType: 'integer',
        default: 2,
        minimum: 1,
        maximum: 3,
        step: 1,
        helpText: '1: 3 Rollers, 2: Pin + Roller (default), 3: Fixed Cantilever Wall.',
      },
      {
        name: 'num_loads',
        label: 'Applied forces',
        valueType: 'integer',
        default: 2,
        minimum: 1,
        maximum: 4,
        step: 1,
        helpText: 'Number of external point forces applied to the rigid body.',
      },
      {
        name: 'num_moments',
        label: 'Applied couple moments',
        valueType: 'integer',
        default: 0,
        minimum: 0,
        maximum: 2,
        step: 1,
        helpText: 'Number of concentrated couple moments applied to the rigid body.',
      },
      {
        name: 'max_force',
        label: 'Max load magnitude (kN)',
        valueType: 'integer',
        default: 5,
        minimum: 1,
        maximum: 20,
        step: 1,
        helpText: 'Upper bound for applied point load magnitudes.',
      },
    ],
  },
]

const LEGACY_RAMP = [3, 3, 4, 4, 5, 5, 6, 6]

function slot(orderIndex: number, numNodes: number): AdminProblemSlot {
  return {
    orderIndex,
    problemType: 'truss',
    params: { num_nodes: numNodes, max_force: 5, load_count: 1 },
    points: 1,
  }
}

function seedAssignments(): AdminAssignmentDetail[] {
  return [
    {
      id: 'eeeeeee1-0000-4000-8000-000000000001',
      courseId: MAE008,
      slug: 'truss-fall-2026',
      title: 'Truss Analysis — Fall 2026',
      isPublished: true,
      audience: 'all',
      problemCount: 8,
      targetedStudentCount: 3,
      dueAt: '2026-12-15T23:59:00Z',
      opensAt: null,
      hardDeadlineAt: null,
      allowLate: false,
      latePenaltyRate: 0,
      revealSolutionsAfterClose: false,
      instructions: 'Determine the internal force in every member.',
      tolerance: 0.01,
      feedbackMode: 'per_field',
      maxAttempts: null,
      problems: LEGACY_RAMP.map((n, i) => slot(i + 1, n)),
      targetEntryIds: [],
    },
    {
      id: 'eeeeeee1-0000-4000-8000-000000000002',
      courseId: MAE008,
      slug: 'truss-quiz-week8',
      title: 'Truss Review Quiz — Week 8',
      isPublished: false,
      audience: 'selected',
      problemCount: 3,
      targetedStudentCount: 1,
      dueAt: '2026-10-30T23:59:00Z',
      opensAt: null,
      hardDeadlineAt: null,
      allowLate: false,
      latePenaltyRate: 0,
      revealSolutionsAfterClose: false,
      instructions: '',
      tolerance: 0.01,
      feedbackMode: 'binary',
      maxAttempts: 3,
      problems: [slot(1, 3), slot(2, 4), slot(3, 5)],
      targetEntryIds: ['aaaaaaa1-0000-4000-8000-000000000001'],
    },
    {
      id: 'eeeeeee1-0000-4000-8000-000000000003',
      courseId: MAE130,
      slug: 'beam-intro-hw1',
      title: 'Beam Reactions — Homework 1',
      isPublished: true,
      audience: 'all',
      problemCount: 6,
      targetedStudentCount: 1,
      dueAt: '2026-11-05T23:59:00Z',
      opensAt: null,
      hardDeadlineAt: null,
      allowLate: false,
      latePenaltyRate: 0,
      revealSolutionsAfterClose: false,
      instructions: '',
      tolerance: 0.01,
      feedbackMode: 'per_field',
      maxAttempts: null,
      problems: [3, 3, 4, 4, 5, 5].map((n, i) => slot(i + 1, n)),
      targetEntryIds: [],
    },
  ]
}

let assignments: AdminAssignmentDetail[] = seedAssignments()
let idCounter = 500

export function resetAssignmentMockState(): void {
  assignments = seedAssignments()
  idCounter = 500
}

const nextId = () =>
  `eeeeeee9-0000-4000-8000-${String(idCounter++).padStart(12, '0')}`

function summarize(a: AdminAssignmentDetail): AdminAssignmentDetail {
  // Derived fields must stay consistent with the slot list.
  return {
    ...a,
    problemCount: a.problems.length,
    targetedStudentCount:
      a.audience === 'all' ? 3 : a.targetEntryIds.length,
  }
}

const notFound = (detail: string) => HttpResponse.json({ detail }, { status: 404 })

/** Stand-in for the generator: pick a fixture roughly matching the joint count. */
function previewPayload(slotSpec: AdminProblemSlot, index: number, seed: number) {
  // Partial<> so the lookup is typed as possibly-undefined, which it is: a slot
  // need not carry every param a problem type declares.
  const params: Partial<Record<string, number>> = slotSpec.params
  const nodes = params['num_nodes'] ?? 3
  const fixture = nodes <= 3 ? truss3node : nodes <= 4 ? truss4node : truss6node
  return { ...fixture, index, prompt: { ...fixture.prompt, notes: [`seed ${String(seed)}`] } }
}

export const assignmentHandlers = [
  http.get(`${BASE}/admin/problem-types`, () => HttpResponse.json(PROBLEM_TYPES)),

  http.get(`${BASE}/admin/courses/:courseId/assignments`, ({ params }) => {
    const courseId = String(params['courseId'])
    return HttpResponse.json(
      assignments.filter((a) => a.courseId === courseId).map(summarize),
    )
  }),

  http.post(`${BASE}/admin/courses/:courseId/assignments`, async ({ params, request }) => {
    const courseId = String(params['courseId'])
    const body = (await request.json()) as Partial<AdminAssignmentDetail>
    const slug = (body.slug ?? '').trim()

    if (assignments.some((a) => a.courseId === courseId && a.slug === slug)) {
      return HttpResponse.json(
        { detail: 'That slug is already used in this course' },
        { status: 409 },
      )
    }

    const created: AdminAssignmentDetail = {
      id: nextId(),
      courseId,
      slug,
      title: body.title ?? '',
      isPublished: false,
      audience: body.audience ?? 'all',
      problemCount: body.problems?.length ?? 0,
      targetedStudentCount: 0,
      dueAt: body.dueAt ?? null,
      opensAt: body.opensAt ?? null,
      hardDeadlineAt: body.hardDeadlineAt ?? null,
      allowLate: body.allowLate ?? false,
      latePenaltyRate: body.latePenaltyRate ?? 0,
      revealSolutionsAfterClose: body.revealSolutionsAfterClose ?? false,
      instructions: body.instructions ?? '',
      tolerance: body.tolerance ?? 0.01,
      feedbackMode: body.feedbackMode ?? 'per_field',
      maxAttempts: body.maxAttempts ?? null,
      problems: body.problems ?? [],
      targetEntryIds: body.targetEntryIds ?? [],
    }
    assignments.push(created)
    return HttpResponse.json(summarize(created), { status: 201 })
  }),

  http.get(`${BASE}/admin/assignments/:assignmentId`, ({ params }) => {
    const found = assignments.find((a) => a.id === params['assignmentId'])
    return found ? HttpResponse.json(summarize(found)) : notFound('No such assignment')
  }),

  http.patch(`${BASE}/admin/assignments/:assignmentId`, async ({ params, request }) => {
    const found = assignments.find((a) => a.id === params['assignmentId'])
    if (!found) return notFound('No such assignment')
    const body = (await request.json()) as Partial<AdminAssignmentDetail>

    if (body.slug !== undefined) {
      const clash = assignments.some(
        (a) => a.id !== found.id && a.courseId === found.courseId && a.slug === body.slug,
      )
      if (clash) {
        return HttpResponse.json(
          { detail: 'That slug is already used in this course' },
          { status: 409 },
        )
      }
    }

    Object.assign(found, body)
    return HttpResponse.json(summarize(found))
  }),

  http.post(`${BASE}/admin/assignments/:assignmentId/publish`, async ({ params, request }) => {
    const found = assignments.find((a) => a.id === params['assignmentId'])
    if (!found) return notFound('No such assignment')
    const body = (await request.json()) as { isPublished?: boolean }

    if (body.isPublished && found.problems.length === 0) {
      return HttpResponse.json(
        { detail: 'Cannot publish an assignment with no problems' },
        { status: 409 },
      )
    }
    found.isPublished = body.isPublished ?? false
    return HttpResponse.json(summarize(found))
  }),

  http.get(
    `${BASE}/admin/assignments/:assignmentId/preview/:index`,
    ({ params, request }) => {
      const found = assignments.find((a) => a.id === params['assignmentId'])
      if (!found) return notFound('No such assignment')
      const index = Number(params['index'])
      const slotSpec = found.problems.find((s) => s.orderIndex === index)
      if (!slotSpec) return notFound('No such problem index')

      const seed = Number(new URL(request.url).searchParams.get('seed') ?? 1)
      return HttpResponse.json(previewPayload(slotSpec, index, seed))
    },
  ),
]
