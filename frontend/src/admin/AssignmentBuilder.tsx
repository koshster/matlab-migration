import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AdminLayout from './AdminLayout'
import ProblemSlotEditor from './ProblemSlotEditor'
import TargetPicker from './TargetPicker'
import PreviewModal from './PreviewModal'
import {
  useAdminAssignment,
  usePublishAssignment,
  useUpdateAssignment,
} from '../api/hooks'
import type { AdminAssignmentDetail, AssignmentUpdateRequest } from '../api/hooks'

/** ISO instant → value for <input type="datetime-local">, and back. */
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocalInput(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

export default function AssignmentBuilder() {
  const { assignmentId = '' } = useParams<{ assignmentId: string }>()
  const navigate = useNavigate()
  const { data: assignment, isLoading, isError, error } = useAdminAssignment(assignmentId)

  const [draft, setDraft] = useState<AdminAssignmentDetail | null>(null)
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)

  const update = useUpdateAssignment(assignmentId, assignment?.courseId ?? '')
  const publish = usePublishAssignment(assignmentId, assignment?.courseId ?? '')

  // Local draft so the whole form is one save, not a request per keystroke.
  useEffect(() => {
    if (assignment) setDraft(assignment)
  }, [assignment])

  if (isLoading || (!draft && !isError)) {
    return (
      <AdminLayout>
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      </AdminLayout>
    )
  }

  if (isError || !draft || !assignment) {
    return (
      <AdminLayout>
        <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
          <p className="text-sm text-gray-600">
            {error?.status === 404
              ? 'That assignment does not exist, or you do not have access to it.'
              : 'Could not load the assignment.'}
          </p>
          <Link to="/admin" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
            Back to courses
          </Link>
        </div>
      </AdminLayout>
    )
  }

  const set = <K extends keyof AdminAssignmentDetail>(
    key: K,
    value: AdminAssignmentDetail[K],
  ) => { setDraft({ ...draft, [key]: value }) }

  const dirty = JSON.stringify(draft) !== JSON.stringify(assignment)
  const canPublish = draft.problems.length > 0

  // Hoisted `function` bodies don't inherit the null-narrowing above, so bind it.
  const current = draft
  const handleSave = () => {
    const body: AssignmentUpdateRequest = {
      title: current.title,
      slug: current.slug,
      instructions: current.instructions,
      dueAt: current.dueAt,
      opensAt: current.opensAt,
      hardDeadlineAt: current.hardDeadlineAt,
      allowLate: current.allowLate,
      revealSolutionsAfterClose: current.revealSolutionsAfterClose,
      tolerance: current.tolerance,
      feedbackMode: current.feedbackMode,
      maxAttempts: current.maxAttempts,
      audience: current.audience,
      targetEntryIds: current.targetEntryIds,
      problems: current.problems,
    }
    update.mutate(body)
  }

  return (
    <AdminLayout
      breadcrumb={
        <Link
          to={`/admin/courses/${draft.courseId}`}
          className="text-gray-500 hover:text-blue-700"
        >
          Back to course
        </Link>
      }
    >
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{draft.title || 'Untitled'}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-gray-500">
            <span
              className={[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                draft.isPublished
                  ? 'bg-green-100 text-green-800'
                  : 'bg-amber-100 text-amber-800',
              ].join(' ')}
            >
              {draft.isPublished ? 'Published' : 'Draft'}
            </span>
            {!draft.isPublished && <span>Students cannot see this yet.</span>}
            {draft.isPublished && (
              <span>
                Visible to{' '}
                {draft.audience === 'all'
                  ? 'everyone in the course'
                  : `${String(draft.targetEntryIds.length)} selected students`}
              </span>
            )}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={handleSave}
            disabled={!dirty || update.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {update.isPending ? 'Saving…' : dirty ? 'Save changes' : 'Saved'}
          </button>
          <button
            onClick={() => { publish.mutate(!draft.isPublished) }}
            disabled={publish.isPending || (!draft.isPublished && !canPublish)}
            title={
              !draft.isPublished && !canPublish
                ? 'Add at least one problem before publishing'
                : undefined
            }
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700 disabled:opacity-50"
          >
            {publish.isPending
              ? 'Working…'
              : draft.isPublished
                ? 'Unpublish'
                : 'Publish'}
          </button>
        </div>
      </div>

      {(update.isError || publish.isError) && (
        <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {(update.error ?? publish.error)?.status === 409
            ? 'That slug is already used in this course, or the assignment has no problems to publish.'
            : 'Could not save. Please try again.'}
        </p>
      )}

      {dirty && (
        <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          You have unsaved changes.
        </p>
      )}

      <div className="flex flex-col gap-6">
        <Section title="Details">
          <div className="grid gap-4 sm:grid-cols-2">
            <Text
              label="Title"
              value={draft.title}
              onChange={(v) => { set('title', v) }}
            />
            <Text
              label="URL slug"
              value={draft.slug}
              help="Appears in the student's address bar."
              onChange={(v) => { set('slug', v) }}
            />
          </div>
          <label className="mt-4 flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">
              Instructions (optional)
            </span>
            <textarea
              rows={3}
              value={draft.instructions}
              onChange={(e) => { set('instructions', e.target.value) }}
              className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </Section>

        <Section title="Schedule and grading">
          <div className="grid gap-4 sm:grid-cols-2">
            <DateTime
              label="Opens at"
              help="Leave blank to open immediately."
              value={draft.opensAt}
              onChange={(v) => { set('opensAt', v) }}
            />
            <DateTime
              label="Due at"
              help={
                draft.allowLate
                  ? 'Advisory while late work is allowed.'
                  : 'Closes the assignment. Leave blank for no deadline.'
              }
              value={draft.dueAt}
              onChange={(v) => { set('dueAt', v) }}
            />
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">Late work</span>
              <span className="flex items-center gap-2 py-1.5">
                <input
                  type="checkbox"
                  checked={draft.allowLate}
                  onChange={(e) => { set('allowLate', e.target.checked) }}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Accept work after the due date</span>
              </span>
              <span className="text-xs text-gray-400">
                When on, the hard deadline is what actually closes it.
              </span>
            </label>
            <DateTime
              label="Hard deadline"
              help="Absolute cutoff. Only used when late work is allowed."
              value={draft.hardDeadlineAt}
              onChange={(v) => { set('hardDeadlineAt', v) }}
            />
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">After closing</span>
              <span className="flex items-center gap-2 py-1.5">
                <input
                  type="checkbox"
                  checked={draft.revealSolutionsAfterClose}
                  onChange={(e) => { set('revealSolutionsAfterClose', e.target.checked) }}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Show students the correct answers</span>
              </span>
              <span className="text-xs text-gray-400">
                Off by default. Solutions are never sent before the assignment closes.
              </span>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">Feedback</span>
              <select
                value={draft.feedbackMode}
                onChange={(e) => {
                  set('feedbackMode', e.target.value as AdminAssignmentDetail['feedbackMode'])
                }}
                className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="per_field">Per answer — say which members are wrong</option>
                <option value="binary">Right or wrong only</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">Attempts allowed</span>
              <input
                type="number"
                min={1}
                placeholder="Unlimited"
                value={draft.maxAttempts ?? ''}
                onChange={(e) => {
                  set('maxAttempts', e.target.value === '' ? null : Number(e.target.value))
                }}
                className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
              <span className="text-xs text-gray-400">Blank means unlimited.</span>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">Answer tolerance</span>
              <input
                type="number"
                min={0}
                step={0.001}
                value={draft.tolerance}
                onChange={(e) => { set('tolerance', Number(e.target.value)) }}
                className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
              <span className="text-xs text-gray-400">
                Relative; 0.01 accepts answers within 1%.
              </span>
            </label>
          </div>
        </Section>

        <Section
          title="Problems"
          subtitle="Each student gets a different randomly generated version of every problem."
        >
          <ProblemSlotEditor
            problems={draft.problems}
            onChange={(problems) => { set('problems', problems) }}
            onPreview={(orderIndex) => { setPreviewIndex(orderIndex) }}
          />
        </Section>

        <Section title="Who gets this">
          <TargetPicker
            courseId={draft.courseId}
            audience={draft.audience}
            targetEntryIds={draft.targetEntryIds}
            onChange={({ audience, targetEntryIds }) => {
              setDraft({ ...draft, audience, targetEntryIds })
            }}
          />
        </Section>
      </div>

      <div className="mt-8 flex justify-between">
        <button
          onClick={() => { navigate(`/admin/courses/${draft.courseId}`) }}
          className="text-sm text-gray-500 hover:underline"
        >
          ← Back to course
        </button>
      </div>

      {previewIndex !== null && (
        <PreviewModal
          assignmentId={assignmentId}
          index={previewIndex}
          onClose={() => { setPreviewIndex(null) }}
        />
      )}
    </AdminLayout>
  )
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="mb-3 mt-0.5 text-sm text-gray-500">{subtitle}</p>}
      <div className={subtitle ? '' : 'mt-3'}>{children}</div>
    </section>
  )
}

function Text({
  label,
  value,
  help,
  onChange,
}: {
  label: string
  value: string
  help?: string
  onChange: (value: string) => void
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <input
        value={value}
        onChange={(e) => { onChange(e.target.value) }}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
      />
      {help && <span className="text-xs text-gray-400">{help}</span>}
    </label>
  )
}

function DateTime({
  label,
  help,
  value,
  onChange,
}: {
  label: string
  help?: string
  value: string | null
  onChange: (value: string | null) => void
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <input
        type="datetime-local"
        value={toLocalInput(value)}
        onChange={(e) => { onChange(fromLocalInput(e.target.value)) }}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
      />
      {help && <span className="text-xs text-gray-400">{help}</span>}
    </label>
  )
}
