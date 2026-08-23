import { useMemo } from 'react'
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
  heading: string
  term: string
  assignments: StudentAssignmentItem[]
}

export default function StudentDashboard() {
  const session = useSession()
  const setSession = useSetSession()
  const navigate = useNavigate()
  const { data: assignments, isLoading, isError } = useStudentAssignments()
  const { data: invitations } = useStudentInvitations()

  function handleLogout() {
    setSession(null)
    navigate('/student/login')
  }

  // Grouped by course so a student in two classes can tell them apart, and so
  // accepting an invitation visibly adds a section.
  const groups = useMemo<CourseGroup[]>(() => {
    const byCourse = new Map<string, CourseGroup>()
    for (const assignment of assignments ?? []) {
      const course = assignment.course
      let group = byCourse.get(course.id)
      if (!group) {
        group = {
          id: course.id,
          heading: course.title ? `${course.code} · ${course.title}` : course.code,
          term: course.term,
          assignments: [],
        }
        byCourse.set(course.id, group)
      }
      group.assignments.push(assignment)
    }
    return [...byCourse.values()]
  }, [assignments])

  const hasInvitations = (invitations?.length ?? 0) > 0

  return (
    <main className="flex min-h-screen flex-col bg-gray-50">
      <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
        <span className="text-sm font-semibold text-gray-800">Statics Platform</span>
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
        <InvitationList />

        <h1 className="mb-6 text-xl font-bold text-gray-900">My Assignments</h1>

        {isLoading && (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600">Failed to load assignments. Please refresh.</p>
        )}

        {assignments && groups.length === 0 && (
          <p className="text-sm text-gray-500">
            {hasInvitations
              ? 'Accept an invitation above to see your assignments.'
              : 'No assignments yet. Once your instructor adds you to a course, an invitation will appear here.'}
          </p>
        )}

        <div className="flex flex-col gap-8">
          {groups.map((group) => (
            <section key={group.id} aria-labelledby={`course-${group.id}`}>
              {/* Only label sections when there is more than one course. */}
              {groups.length > 1 && (
                <h2
                  id={`course-${group.id}`}
                  className="mb-3 text-sm font-semibold text-gray-700"
                >
                  {group.heading}
                  <span className="ml-2 font-normal text-gray-400">{group.term}</span>
                </h2>
              )}
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
                      onClick={() => {
                        navigate(
                          a.status === 'submitted'
                            ? `/assignment/${a.slug}/submitted`
                            : `/assignment/${a.slug}`,
                        )
                      }}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                    >
                      {a.status === 'submitted' ? 'View Results' : 'Open'}
                    </button>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  )
}
