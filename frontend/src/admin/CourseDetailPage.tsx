import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AdminLayout from './AdminLayout'
import RosterTable from './RosterTable'
import RosterImportPanel from './RosterImportPanel'
import StaffTab from './StaffTab'
import { useCourse, useUpdateCourse } from '../api/hooks'

type Tab = 'roster' | 'assignments' | 'staff'

const TABS: { key: Tab; label: string }[] = [
  { key: 'roster', label: 'Roster' },
  { key: 'assignments', label: 'Assignments' },
  { key: 'staff', label: 'Staff' },
]

export default function CourseDetailPage() {
  const { courseId = '' } = useParams<{ courseId: string }>()
  const { data: course, isLoading, isError, error } = useCourse(courseId)
  const [tab, setTab] = useState<Tab>('roster')
  const [importing, setImporting] = useState(false)
  const updateMutation = useUpdateCourse(courseId)

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      </AdminLayout>
    )
  }

  if (isError || !course) {
    // The API returns 404 rather than 403 for a course you have no role on, so
    // these are deliberately the same message.
    return (
      <AdminLayout>
        <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
          <p className="text-sm text-gray-600">
            {error?.status === 404
              ? 'That course does not exist, or you do not have access to it.'
              : 'Could not load the course.'}
          </p>
          <Link
            to="/admin"
            className="mt-3 inline-block text-sm text-blue-600 hover:underline"
          >
            Back to courses
          </Link>
        </div>
      </AdminLayout>
    )
  }

  const canManageRoster = course.viewerRole === 'owner' || course.viewerRole === 'instructor'

  return (
    <AdminLayout
      breadcrumb={
        <span className="text-gray-500">
          {course.code} §{course.section}
        </span>
      }
    >
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {course.code}
            <span className="ml-2 text-base font-normal text-gray-400">
              §{course.section}
            </span>
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {course.title ? `${course.title} · ` : ''}
            {course.term} · {course.studentCount} enrolled
            {course.pendingInviteCount > 0 && (
              <span className="text-amber-600">
                {' '}
                · {course.pendingInviteCount} pending
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {course.viewerRole === 'owner' && (
            <button
              onClick={() => {
                updateMutation.mutate({ isArchived: !course.isArchived })
              }}
              disabled={updateMutation.isPending}
              className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
            >
              {course.isArchived ? 'Unarchive' : 'Archive'}
            </button>
          )}
          {tab === 'roster' && canManageRoster && (
            <button
              onClick={() => { setImporting((v) => !v) }}
              className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              {importing ? 'Cancel' : 'Add students'}
            </button>
          )}
        </div>
      </div>

      <div className="mb-5 flex gap-1 border-b border-gray-200" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => { setTab(t.key) }}
            className={[
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors',
              tab === t.key
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'roster' && (
        <>
          {importing && (
            <RosterImportPanel
              courseId={courseId}
              onClose={() => { setImporting(false) }}
            />
          )}
          <RosterTable courseId={courseId} />
        </>
      )}

      {tab === 'assignments' && (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-600">
            {course.assignmentCount === 0
              ? 'No assignments yet.'
              : `${String(course.assignmentCount)} assignment${course.assignmentCount === 1 ? '' : 's'}.`}
          </p>
          <p className="mt-1 text-sm text-gray-400">
            The assignment builder is the next slice of work.
          </p>
        </div>
      )}

      {tab === 'staff' && (
        <StaffTab courseId={courseId} canManage={course.viewerRole === 'owner'} />
      )}
    </AdminLayout>
  )
}
