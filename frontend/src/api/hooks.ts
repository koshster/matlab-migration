import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '@statics/contract/src/index'
import apiFetch, { ApiError } from './client'

type AssignmentSummary = components['schemas']['AssignmentSummary']
type ProblemPayload = components['schemas']['ProblemPayload']
type AnswersRequest = components['schemas']['AnswersRequest']
export type { ApiError }
type SavedResponse = components['schemas']['SavedResponse']
type CheckResult = components['schemas']['CheckResult']
type SubmissionResult = components['schemas']['SubmissionResult']
type StudentLoginRequest = components['schemas']['StudentLoginRequest']
type StudentRegisterRequest = components['schemas']['StudentRegisterRequest']
type StudentAuthResponse = components['schemas']['StudentAuthResponse']
type StudentAssignmentItem = components['schemas']['StudentAssignmentListItem']
type InstructorLoginRequest = components['schemas']['InstructorLoginRequest']
type InstructorRegisterRequest = components['schemas']['InstructorRegisterRequest']
type InstructorAuthResponse = components['schemas']['InstructorAuthResponse']
type InstructorRecord = components['schemas']['InstructorRecord']
type OkResponse = components['schemas']['OkResponse']

export type {
  AssignmentSummary,
  ProblemPayload,
  CheckResult,
  SubmissionResult,
  StudentAssignmentItem,
  InstructorRecord,
}

// ---------------------------------------------------------------------------
// Keys
// ---------------------------------------------------------------------------
const keys = {
  assignment: (slug: string) => ['assignment', slug] as const,
  problem: (slug: string, index: number) => ['problem', slug, index] as const,
  result: (slug: string) => ['result', slug] as const,
  instructorMe: () => ['instructor', 'me'] as const,
}

// ---------------------------------------------------------------------------
// Student auth
// ---------------------------------------------------------------------------

export function useStudentLogin() {
  return useMutation<StudentAuthResponse, ApiError, StudentLoginRequest>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/student/login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useStudentRegister() {
  return useMutation<StudentAuthResponse, ApiError, StudentRegisterRequest>({
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

export function useInstructorLogin() {
  return useMutation<InstructorAuthResponse, ApiError, InstructorLoginRequest>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/instructor/login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useInstructorRegister() {
  return useMutation<InstructorAuthResponse, ApiError, InstructorRegisterRequest>({
    mutationFn: (body) =>
      apiFetch('/api/v1/auth/instructor/register', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useInstructorLogout() {
  const qc = useQueryClient()
  return useMutation<OkResponse, ApiError>({
    mutationFn: () => apiFetch('/api/v1/auth/instructor/logout', { method: 'POST' }),
    onSuccess: () => {
      // Drop any admin data cached under the old session.
      qc.removeQueries({ queryKey: keys.instructorMe() })
    },
  })
}

/**
 * Resolves the instructor from the httpOnly cookie. InstructorContext keeps a
 * sessionStorage copy purely as a UI gate, and that copy can outlive the
 * cookie — this is the authoritative check.
 */
export function useInstructorMe(enabled = true) {
  return useQuery<InstructorAuthResponse>({
    queryKey: keys.instructorMe(),
    queryFn: () => apiFetch('/api/v1/auth/instructor/me'),
    enabled,
    retry: false,
  })
}

export function useStudentLogout() {
  return useMutation<OkResponse, ApiError>({
    mutationFn: () => apiFetch('/api/v1/auth/student/logout', { method: 'POST' }),
  })
}

// ---------------------------------------------------------------------------
// Admin — courses, roster, staff
// ---------------------------------------------------------------------------

type CourseSummary = components['schemas']['CourseSummary']
type CourseCreateRequest = components['schemas']['CourseCreateRequest']
type CourseUpdateRequest = components['schemas']['CourseUpdateRequest']
type RosterEntry = components['schemas']['RosterEntry']
type RosterImportRequest = components['schemas']['RosterImportRequest']
type RosterImportResult = components['schemas']['RosterImportResult']
type RosterEntryUpdateRequest = components['schemas']['RosterEntryUpdateRequest']
type CourseStaffMember = components['schemas']['CourseStaffMember']
type CourseStaffAddRequest = components['schemas']['CourseStaffAddRequest']
type CourseRole = components['schemas']['CourseRole']

export type {
  CourseSummary,
  CourseRole,
  RosterEntry,
  RosterImportResult,
  CourseStaffMember,
}

const adminKeys = {
  courses: () => ['admin', 'courses'] as const,
  course: (id: string) => ['admin', 'course', id] as const,
  roster: (id: string) => ['admin', 'course', id, 'roster'] as const,
  staff: (id: string) => ['admin', 'course', id, 'staff'] as const,
}

export function useCourses() {
  return useQuery<CourseSummary[], ApiError>({
    queryKey: adminKeys.courses(),
    queryFn: () => apiFetch('/api/v1/admin/courses'),
  })
}

export function useCourse(courseId: string) {
  return useQuery<CourseSummary, ApiError>({
    queryKey: adminKeys.course(courseId),
    queryFn: () => apiFetch(`/api/v1/admin/courses/${courseId}`),
    enabled: !!courseId,
  })
}

export function useCreateCourse() {
  const qc = useQueryClient()
  return useMutation<CourseSummary, ApiError, CourseCreateRequest>({
    mutationFn: (body) =>
      apiFetch('/api/v1/admin/courses', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminKeys.courses() })
    },
  })
}

export function useUpdateCourse(courseId: string) {
  const qc = useQueryClient()
  return useMutation<CourseSummary, ApiError, CourseUpdateRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/admin/courses/${courseId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (course) => {
      qc.setQueryData(adminKeys.course(courseId), course)
      void qc.invalidateQueries({ queryKey: adminKeys.courses() })
    },
  })
}

export function useRoster(courseId: string) {
  return useQuery<RosterEntry[], ApiError>({
    queryKey: adminKeys.roster(courseId),
    queryFn: () => apiFetch(`/api/v1/admin/courses/${courseId}/roster`),
    enabled: !!courseId,
  })
}

export function useAddRosterEntries(courseId: string) {
  const qc = useQueryClient()
  return useMutation<RosterImportResult, ApiError, RosterImportRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/admin/courses/${courseId}/roster`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminKeys.roster(courseId) })
      // Roster changes move the course-list counts.
      void qc.invalidateQueries({ queryKey: adminKeys.courses() })
      void qc.invalidateQueries({ queryKey: adminKeys.course(courseId) })
    },
  })
}

export function useUpdateRosterEntry(courseId: string) {
  const qc = useQueryClient()
  return useMutation<
    RosterEntry,
    ApiError,
    { entryId: string; body: RosterEntryUpdateRequest }
  >({
    mutationFn: ({ entryId, body }) =>
      apiFetch(`/api/v1/admin/courses/${courseId}/roster/${entryId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminKeys.roster(courseId) })
      void qc.invalidateQueries({ queryKey: adminKeys.courses() })
      void qc.invalidateQueries({ queryKey: adminKeys.course(courseId) })
    },
  })
}

export function useCourseStaff(courseId: string) {
  return useQuery<CourseStaffMember[], ApiError>({
    queryKey: adminKeys.staff(courseId),
    queryFn: () => apiFetch(`/api/v1/admin/courses/${courseId}/staff`),
    enabled: !!courseId,
  })
}

export function useAddCourseStaff(courseId: string) {
  const qc = useQueryClient()
  return useMutation<CourseStaffMember, ApiError, CourseStaffAddRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/admin/courses/${courseId}/staff`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminKeys.staff(courseId) })
    },
  })
}
