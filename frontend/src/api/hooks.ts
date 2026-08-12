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
// Student session
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
