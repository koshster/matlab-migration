import { useState } from 'react'
import { Link } from 'react-router-dom'
import AdminLayout from './AdminLayout'
import { useCourses, useCreateCourse } from '../api/hooks'
import type { CourseSummary } from '../api/hooks'

export default function CoursesPage() {
  const { data: courses, isLoading, isError } = useCourses()
  const [showArchived, setShowArchived] = useState(false)
  const [creating, setCreating] = useState(false)

  const visible = (courses ?? []).filter((c) => showArchived || !c.isArchived)
  const archivedCount = (courses ?? []).filter((c) => c.isArchived).length

  return (
    <AdminLayout>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Courses</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage rosters and assignments for each section you teach.
          </p>
        </div>
        <button
          onClick={() => { setCreating((v) => !v) }}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {creating ? 'Cancel' : 'New course'}
        </button>
      </div>

      {creating && <CreateCourseForm onDone={() => { setCreating(false) }} />}

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {isError && (
        <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">
          Could not load courses. Check your connection and reload.
        </p>
      )}

      {courses && visible.length === 0 && (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            No courses yet. Create one to start building a roster.
          </p>
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {visible.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </ul>

      {archivedCount > 0 && (
        <button
          onClick={() => { setShowArchived((v) => !v) }}
          className="mt-4 text-sm text-gray-500 underline hover:text-gray-700"
        >
          {showArchived
            ? 'Hide archived courses'
            : `Show ${archivedCount} archived course${archivedCount === 1 ? '' : 's'}`}
        </button>
      )}
    </AdminLayout>
  )
}

function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <li>
      <Link
        to={`/admin/courses/${course.id}`}
        className="block rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-blue-400"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-gray-900">
                {course.code}
                <span className="ml-2 text-sm font-normal text-gray-400">
                  §{course.section}
                </span>
              </h2>
              {course.isArchived && (
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                  Archived
                </span>
              )}
              {course.viewerRole !== 'owner' && (
                <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                  {course.viewerRole}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm text-gray-500">
              {course.title ? `${course.title} · ` : ''}
              {course.term}
            </p>
          </div>
          <dl className="flex gap-6 text-right">
            <Stat label="Students" value={course.studentCount} />
            <Stat
              label="Pending"
              value={course.pendingInviteCount}
              highlight={course.pendingInviteCount > 0}
            />
            <Stat label="Assignments" value={course.assignmentCount} />
          </dl>
        </div>
      </Link>
    </li>
  )
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: number
  highlight?: boolean
}) {
  return (
    <div>
      <dd
        className={[
          'text-lg font-semibold',
          highlight ? 'text-amber-600' : 'text-gray-900',
        ].join(' ')}
      >
        {value}
      </dd>
      <dt className="text-xs uppercase tracking-wide text-gray-400">{label}</dt>
    </div>
  )
}

function CreateCourseForm({ onDone }: { onDone: () => void }) {
  const [fields, setFields] = useState({
    code: '',
    term: '',
    section: '001',
    title: '',
  })
  const createMutation = useCreateCourse()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createMutation.mutate(fields, { onSuccess: onDone })
  }

  const canSubmit = fields.code.trim() !== '' && fields.term.trim() !== ''

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-4"
    >
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Field
          label="Course code"
          value={fields.code}
          placeholder="MAE-008"
          onChange={(v) => { setFields((f) => ({ ...f, code: v })) }}
        />
        <Field
          label="Term"
          value={fields.term}
          placeholder="Fall 2026"
          onChange={(v) => { setFields((f) => ({ ...f, term: v })) }}
        />
        <Field
          label="Section"
          value={fields.section}
          placeholder="001"
          onChange={(v) => { setFields((f) => ({ ...f, section: v })) }}
        />
        <Field
          label="Title (optional)"
          value={fields.title}
          placeholder="Statics"
          onChange={(v) => { setFields((f) => ({ ...f, title: v })) }}
        />
      </div>

      {createMutation.isError && (
        <p className="mt-3 text-sm text-red-600">
          {createMutation.error.status === 409
            ? 'A course with that code, term and section already exists.'
            : 'Could not create the course. Try again.'}
        </p>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onDone}
          className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!canSubmit || createMutation.isPending}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {createMutation.isPending ? 'Creating…' : 'Create course'}
        </button>
      </div>
    </form>
  )
}

function Field({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder: string
  onChange: (value: string) => void
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => { onChange(e.target.value) }}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </label>
  )
}
