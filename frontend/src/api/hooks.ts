import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '@statics/contract/src/index'
import apiFetch, { ApiError } from './client'

type AssignmentSummary = components['schemas']['AssignmentSummary']
type ProblemPayload = components['schemas']['ProblemPayload']
type StudentSessionRequest = components['schemas']['StudentSessionRequest']
type StudentSessionResponse = components['schemas']['StudentSessionResponse']
type AnswersRequest = components['schemas']['AnswersRequest']
export type { ApiError }
type SavedResponse = components['schemas']['SavedResponse']
type CheckResult = components['schemas']['CheckResult']
type SubmissionResult = components['schemas']['SubmissionResult']

export type { AssignmentSummary, ProblemPayload, CheckResult, SubmissionResult }

// ---------------------------------------------------------------------------
// Keys
// ---------------------------------------------------------------------------
const keys = {
  assignment: (slug: string) => ['assignment', slug] as const,
  problem: (slug: string, index: number) => ['problem', slug, index] as const,
  result: (slug: string) => ['result', slug] as const,
}

// ---------------------------------------------------------------------------
// Student session (legacy — kept for MSW compatibility)
// ---------------------------------------------------------------------------
export function useStudentSession() {
  return useMutation<StudentSessionResponse, ApiError, StudentSessionRequest>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/student/session', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

// ---------------------------------------------------------------------------
// Student auth (new secure endpoints)
// ---------------------------------------------------------------------------

interface StudentRecord {
  id: string
  firstName: string
  lastName: string
}

interface StudentAuthResponse {
  student: StudentRecord
}

export function useStudentLogin() {
  return useMutation<StudentAuthResponse, ApiError, { pid: string; password: string }>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/student/login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useStudentRegister() {
  return useMutation<StudentAuthResponse, ApiError, { pid: string; firstName: string; lastName: string; password: string }>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/student/register', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

// ---------------------------------------------------------------------------
// Student assignment list (dashboard)
// ---------------------------------------------------------------------------

export interface StudentAssignmentItem {
  slug: string
  title: string
  status: 'not_started' | 'in_progress' | 'submitted'
  score: { earned: number; total: number } | null
  dueAt: string | null
  problemCount: number
}

export function useStudentAssignments() {
  return useQuery<StudentAssignmentItem[]>({
    queryKey: ['student-assignments'],
    queryFn: () => apiFetch('/api/v1/student/assignments'),
  })
}

// ---------------------------------------------------------------------------
// Assignment
// ---------------------------------------------------------------------------
export function useAssignment(slug: string) {
  return useQuery<AssignmentSummary>({
    queryKey: keys.assignment(slug),
    queryFn: () => apiFetch(`/api/v1/assignments/${slug}`),
    enabled: !!slug,
  })
}

// ---------------------------------------------------------------------------
// Problem
// ---------------------------------------------------------------------------
export function useProblem(slug: string, index: number | null) {
  return useQuery<ProblemPayload>({
    queryKey: index !== null ? keys.problem(slug, index) : ['problem-disabled'],
    queryFn: () => apiFetch(`/api/v1/assignments/${slug}/problems/${index}`),
    enabled: !!slug && index !== null,
  })
}

// ---------------------------------------------------------------------------
// Save answers
// ---------------------------------------------------------------------------
export function useSaveAnswers(slug: string, index: number) {
  return useMutation<SavedResponse, ApiError, AnswersRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/assignments/${slug}/problems/${index}/answers`, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
  })
}

// ---------------------------------------------------------------------------
// Check answers
// ---------------------------------------------------------------------------
export function useCheckAnswers(slug: string, index: number) {
  const qc = useQueryClient()
  return useMutation<CheckResult, ApiError, AnswersRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/assignments/${slug}/problems/${index}/check`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.assignment(slug) })
    },
  })
}

// ---------------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------------
export function useSubmit(slug: string) {
  const qc = useQueryClient()
  return useMutation<SubmissionResult, ApiError>({
    mutationFn: () =>
      apiFetch(`/api/v1/assignments/${slug}/submit`, { method: 'POST' }),
    onSuccess: (data) => {
      qc.setQueryData(keys.result(slug), data)
      void qc.invalidateQueries({ queryKey: keys.assignment(slug) })
    },
  })
}

// ---------------------------------------------------------------------------
// Result (after submit)
// ---------------------------------------------------------------------------
export function useResult(slug: string) {
  return useQuery<SubmissionResult>({
    queryKey: keys.result(slug),
    queryFn: () => apiFetch(`/api/v1/assignments/${slug}/result`),
    enabled: !!slug,
  })
}

// ---------------------------------------------------------------------------
// Instructor auth
// ---------------------------------------------------------------------------

interface InstructorRecord {
  id: string
  email: string
  name: string
}

interface InstructorResponse {
  instructor: InstructorRecord
}

export function useInstructorLogin() {
  return useMutation<InstructorResponse, ApiError, { email: string; password: string }>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/instructor/login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useInstructorRegister() {
  return useMutation<InstructorResponse, ApiError, { name: string; email: string; password: string }>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/instructor/register', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useInstructorLogout() {
  return useMutation<{ ok: boolean }, ApiError, void>({
    mutationFn: () =>
      apiFetch('/api/v1/auth/instructor/logout', { method: 'POST' }),
  })
}
