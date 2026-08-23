import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCourseAssignments, useCreateAssignment } from '../api/hooks'
import type { AdminAssignmentSummary } from '../api/hooks'

function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 128)
}

export default function AssignmentsTab({
  courseId,
  canManage,
}: {
  courseId: string
  canManage: boolean
}) {
  const { data: assignments, isLoading, isError } = useCourseAssignments(courseId)
  const [creating, setCreating] = useState(false)

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">
        Could not load assignments.
      </p>
    )
  }

  const list = assignments ?? []

  return (
    <div>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <button
            onClick={() => { setCreating((v) => !v) }}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            {creating ? 'Cancel' : 'New assignment'}
          </button>
        </div>
      )}

      {creating && (
        <CreateAssignmentForm
          courseId={courseId}
          onCancel={() => { setCreating(false) }}
        />
      )}

      {list.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            No assignments yet.
            {canManage ? ' Create one to start building a problem set.' : ''}
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {list.map((assignment) => (
            <AssignmentRow key={assignment.id} assignment={assignment} />
          ))}
        </ul>
      )}
    </div>
  )
}

function AssignmentRow({ assignment }: { assignment: AdminAssignmentSummary }) {
  const navigate = useNavigate()

  return (
    <li>
      <button
        onClick={() => { navigate(`/admin/assignments/${assignment.id}`) }}
        className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white p-4 text-left transition-colors hover:border-blue-400"
      >
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-900">{assignment.title}</span>
            <span
              className={[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                assignment.isPublished
                  ? 'bg-green-100 text-green-800'
                  : 'bg-amber-100 text-amber-800',
              ].join(' ')}
            >
              {assignment.isPublished ? 'Published' : 'Draft'}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-gray-500">
            {assignment.problemCount}{' '}
            {assignment.problemCount === 1 ? 'problem' : 'problems'} ·{' '}
            {assignment.audience === 'all'
              ? 'everyone in the course'
              : `${String(assignment.targetedStudentCount)} selected`}
            {assignment.dueAt
              ? ` · due ${new Date(assignment.dueAt).toLocaleDateString()}`
              : ''}
          </p>
        </div>
        <span aria-hidden="true" className="text-gray-300">
          →
        </span>
      </button>
    </li>
  )
}

function CreateAssignmentForm({
  courseId,
  onCancel,
}: {
  courseId: string
  onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [slugEdited, setSlugEdited] = useState(false)
  const navigate = useNavigate()
  const create = useCreateAssignment(courseId)

  // Slug follows the title until the instructor overrides it.
  const effectiveSlug = slugEdited ? slug : slugify(title)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    create.mutate(
      { title: title.trim(), slug: effectiveSlug, audience: 'all', problems: [] },
      {
        onSuccess: (created) => {
          // Straight into the builder — a new assignment has no problems yet.
          navigate(`/admin/assignments/${created.id}`)
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Title</span>
          <input
            value={title}
            onChange={(e) => { setTitle(e.target.value) }}
            placeholder="Homework 1"
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">URL slug</span>
          <input
            value={effectiveSlug}
            onChange={(e) => {
              setSlugEdited(true)
              setSlug(e.target.value)
            }}
            placeholder="homework-1"
            className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
      </div>

      {create.isError && (
        <p className="mt-3 text-sm text-red-600">
          {create.error.status === 409
            ? 'An assignment with that slug already exists in this course.'
            : 'Could not create the assignment. Try again.'}
        </p>
      )}

      <p className="mt-3 text-xs text-gray-500">
        Created as a draft — you add problems next, and students see nothing until
        you publish.
      </p>

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={title.trim() === '' || effectiveSlug === '' || create.isPending}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {create.isPending ? 'Creating…' : 'Create and add problems'}
        </button>
      </div>
    </form>
  )
}
