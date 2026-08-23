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

// ---------------------------------------------------------------------------
// Student — courses and invitations
// ---------------------------------------------------------------------------

type StudentInvitation = components['schemas']['StudentInvitation']
type StudentCourseSummary = components['schemas']['StudentCourseSummary']

export type { StudentInvitation, StudentCourseSummary }

const studentKeys = {
  invitations: () => ['student', 'invitations'] as const,
  courses: () => ['student', 'courses'] as const,
  assignments: () => ['student-assignments'] as const,
}

export function useStudentInvitations() {
  return useQuery<StudentInvitation[], ApiError>({
    queryKey: studentKeys.invitations(),
    queryFn: () => apiFetch('/api/v1/student/invitations'),
  })
}

export function useStudentCourses() {
  return useQuery<StudentCourseSummary[], ApiError>({
    queryKey: studentKeys.courses(),
    queryFn: () => apiFetch('/api/v1/student/courses'),
  })
}

/**
 * Accepting is what makes a course's assignments visible, so the assignment
 * list must be refetched alongside the invitation list.
 */
export function useAcceptInvitation() {
  const qc = useQueryClient()
  return useMutation<StudentCourseSummary, ApiError, string>({
    mutationFn: (entryId) =>
      apiFetch(`/api/v1/student/invitations/${entryId}/accept`, { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: studentKeys.invitations() })
      void qc.invalidateQueries({ queryKey: studentKeys.courses() })
      void qc.invalidateQueries({ queryKey: studentKeys.assignments() })
    },
  })
}

export function useDeclineInvitation() {
  const qc = useQueryClient()
  return useMutation<OkResponse, ApiError, string>({
    mutationFn: (entryId) =>
      apiFetch(`/api/v1/student/invitations/${entryId}/decline`, { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: studentKeys.invitations() })
    },
  })
}

// ---------------------------------------------------------------------------
// Admin — assignments
// ---------------------------------------------------------------------------

type ProblemTypeInfo = components['schemas']['ProblemTypeInfo']
type ParamFieldSpec = components['schemas']['ParamFieldSpec']
type AdminAssignmentSummary = components['schemas']['AdminAssignmentSummary']
type AdminAssignmentDetail = components['schemas']['AdminAssignmentDetail']
type AdminProblemSlot = components['schemas']['AdminProblemSlot']
type AssignmentCreateRequest = components['schemas']['AssignmentCreateRequest']
type AssignmentUpdateRequest = components['schemas']['AssignmentUpdateRequest']

export type {
  ProblemTypeInfo,
  ParamFieldSpec,
  AdminAssignmentSummary,
  AdminAssignmentDetail,
  AdminProblemSlot,
  AssignmentUpdateRequest,
}

const assignmentKeys = {
  problemTypes: () => ['admin', 'problem-types'] as const,
  list: (courseId: string) => ['admin', 'course', courseId, 'assignments'] as const,
  detail: (id: string) => ['admin', 'assignment', id] as const,
  preview: (id: string, index: number, seed: number) =>
    ['admin', 'assignment', id, 'preview', index, seed] as const,
}

/** The catalogue the builder renders its difficulty form from. */
export function useProblemTypes() {
  return useQuery<ProblemTypeInfo[], ApiError>({
    queryKey: assignmentKeys.problemTypes(),
    queryFn: () => apiFetch('/api/v1/admin/problem-types'),
    // The registry only changes on deploy.
    staleTime: Infinity,
  })
}

export function useCourseAssignments(courseId: string) {
  return useQuery<AdminAssignmentSummary[], ApiError>({
    queryKey: assignmentKeys.list(courseId),
    queryFn: () => apiFetch(`/api/v1/admin/courses/${courseId}/assignments`),
    enabled: !!courseId,
  })
}

export function useAdminAssignment(assignmentId: string) {
  return useQuery<AdminAssignmentDetail, ApiError>({
    queryKey: assignmentKeys.detail(assignmentId),
    queryFn: () => apiFetch(`/api/v1/admin/assignments/${assignmentId}`),
    enabled: !!assignmentId,
  })
}

export function useCreateAssignment(courseId: string) {
  const qc = useQueryClient()
  return useMutation<AdminAssignmentDetail, ApiError, AssignmentCreateRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/admin/courses/${courseId}/assignments`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: assignmentKeys.list(courseId) })
    },
  })
}

export function useUpdateAssignment(assignmentId: string, courseId: string) {
  const qc = useQueryClient()
  return useMutation<AdminAssignmentDetail, ApiError, AssignmentUpdateRequest>({
    mutationFn: (body) =>
      apiFetch(`/api/v1/admin/assignments/${assignmentId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      qc.setQueryData(assignmentKeys.detail(assignmentId), updated)
      void qc.invalidateQueries({ queryKey: assignmentKeys.list(courseId) })
      // Slot or param changes invalidate any cached preview.
      void qc.invalidateQueries({ queryKey: ['admin', 'assignment', assignmentId, 'preview'] })
    },
  })
}

export function usePublishAssignment(assignmentId: string, courseId: string) {
  const qc = useQueryClient()
  return useMutation<AdminAssignmentDetail, ApiError, boolean>({
    mutationFn: (isPublished) =>
      apiFetch(`/api/v1/admin/assignments/${assignmentId}/publish`, {
        method: 'POST',
        body: JSON.stringify({ isPublished }),
      }),
    onSuccess: (updated) => {
      qc.setQueryData(assignmentKeys.detail(assignmentId), updated)
      void qc.invalidateQueries({ queryKey: assignmentKeys.list(courseId) })
    },
  })
}

export function useAssignmentPreview(
  assignmentId: string,
  index: number | null,
  seed: number,
) {
  return useQuery<ProblemPayload, ApiError>({
    queryKey: assignmentKeys.preview(assignmentId, index ?? 0, seed),
    queryFn: () =>
      apiFetch(
        `/api/v1/admin/assignments/${assignmentId}/preview/${String(index)}?seed=${String(seed)}`,
      ),
    enabled: !!assignmentId && index !== null,
  })
}
