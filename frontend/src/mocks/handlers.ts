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
]
