import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStudentAssignments, useStudentInvitations } from '../api/hooks'
import type { StudentAssignmentItem } from '../api/hooks'
import { useSession, useSetSession } from '../context/SessionContext'
import InvitationList from './InvitationList'

const statusLabel: Record<string, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  submitted: 'Submitted',
}

const statusStyle: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-green-100 text-green-700',
}

interface CourseGroup {
  id: string
  code: string
  term: string
  title: string
  assignments: StudentAssignmentItem[]
}

export default function StudentDashboard() {
  const session = useSession()
  const setSession = useSetSession()
  const navigate = useNavigate()
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null)

  const { data: assignments, isLoading, isError } = useStudentAssignments()
  const { data: invitations } = useStudentInvitations()

  function handleLogout() {
    setSession(null)
    navigate('/student/login')
  }

  const groups = useMemo<CourseGroup[]>(() => {
    const byCourse = new Map<string, CourseGroup>()
    for (const a of assignments ?? []) {
      const c = a.course
      if (!byCourse.has(c.id)) {
        byCourse.set(c.id, { id: c.id, code: c.code, term: c.term, title: c.title ?? '', assignments: [] })
      }
      byCourse.get(c.id)!.assignments.push(a)
    }
    return [...byCourse.values()]
  }, [assignments])

  const selectedGroup = selectedCourseId ? groups.find((g) => g.id === selectedCourseId) ?? null : null
  const hasInvitations = (invitations?.length ?? 0) > 0

  return (
    <main className="flex min-h-screen flex-col bg-gray-50">
      <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
        <button
          onClick={() => setSelectedCourseId(null)}
          className="text-sm font-semibold text-gray-800 hover:text-blue-600"
        >
          Statics Platform
        </button>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            {session.firstName} {session.lastName}
          </span>
          <button
            onClick={handleLogout}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="mx-auto w-full max-w-3xl px-6 py-8">
        {selectedGroup ? (
          <CourseAssignments
            group={selectedGroup}
            onBack={() => setSelectedCourseId(null)}
            onOpen={(slug, submitted) =>
              navigate(submitted ? `/assignment/${slug}/submitted` : `/assignment/${slug}`)
            }
          />
        ) : (
          <CourseList
            groups={groups}
            isLoading={isLoading}
            isError={isError}
            hasInvitations={hasInvitations}
            onSelectCourse={setSelectedCourseId}
          />
        )}
      </div>
    </main>
  )
}

// ---------------------------------------------------------------------------
// Course list view
// ---------------------------------------------------------------------------

interface CourseListProps {
  groups: CourseGroup[]
  isLoading: boolean
  isError: boolean
  hasInvitations: boolean
  onSelectCourse: (id: string) => void
}

function CourseList({ groups, isLoading, isError, hasInvitations, onSelectCourse }: CourseListProps) {
  return (
    <>
      <InvitationList />

      <h1 className="mb-6 text-xl font-bold text-gray-900">My Courses</h1>

      {isLoading && (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-600">Failed to load courses. Please refresh.</p>
      )}

      {!isLoading && !isError && groups.length === 0 && (
        <p className="text-sm text-gray-500">
          {hasInvitations
            ? 'Accept an invitation above to join a course.'
            : 'No courses yet. Once your instructor adds you to a course, an invitation will appear here.'}
        </p>
      )}

      <div className="flex flex-col gap-4">
        {groups.map((g) => {
          const done = g.assignments.filter((a) => a.status === 'submitted').length
          const inProgress = g.assignments.filter((a) => a.status === 'in_progress').length
          return (
            <button
              key={g.id}
              onClick={() => onSelectCourse(g.id)}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-6 py-5 shadow-sm text-left hover:border-blue-300 hover:shadow-md transition-all"
            >
              <div>
                <p className="text-base font-semibold text-gray-900">
                  {g.code}{g.title ? ` — ${g.title}` : ''}
                </p>
                <p className="mt-0.5 text-sm text-gray-400">{g.term}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {g.assignments.length} assignment{g.assignments.length !== 1 ? 's' : ''}
                  {inProgress > 0 && ` · ${inProgress} in progress`}
                  {done > 0 && ` · ${done} submitted`}
                </p>
              </div>
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )
        })}
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Assignment list for a selected course
// ---------------------------------------------------------------------------

interface CourseAssignmentsProps {
  group: CourseGroup
  onBack: () => void
  onOpen: (slug: string, submitted: boolean) => void
}

function CourseAssignments({ group, onBack, onOpen }: CourseAssignmentsProps) {
  return (
    <>
      <button
        onClick={onBack}
        className="mb-6 flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        My Courses
      </button>

      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">
          {group.code}{group.title ? ` — ${group.title}` : ''}
        </h1>
        <p className="text-sm text-gray-400">{group.term}</p>
      </div>

      <div className="flex flex-col gap-4">
        {group.assignments.map((a) => (
          <div
            key={a.slug}
            className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-6 py-4 shadow-sm"
          >
            <div className="flex flex-col gap-1">
              <span className="text-sm font-semibold text-gray-900">{a.title}</span>
              <div className="flex items-center gap-3">
                <span
                  className={[
                    'rounded-full px-2 py-0.5 text-xs font-medium',
                    statusStyle[a.status] ?? 'bg-gray-100 text-gray-600',
                  ].join(' ')}
                >
                  {statusLabel[a.status] ?? a.status}
                </span>
                {a.dueAt && (
                  <span className="text-xs text-gray-400">
                    Due {new Date(a.dueAt).toLocaleDateString()}
                  </span>
                )}
                {a.score && (
                  <span className="text-xs font-medium text-gray-600">
                    {a.score.earned}/{a.score.total} correct
                  </span>
                )}
              </div>
            </div>

            <button
              onClick={() => onOpen(a.slug, a.status === 'submitted')}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              {a.status === 'submitted' ? 'View Results' : 'Open'}
            </button>
          </div>
        ))}
      </div>
    </>
  )
}
