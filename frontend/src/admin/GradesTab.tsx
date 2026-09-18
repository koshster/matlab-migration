import { useMemo, useState } from 'react'
import {
  useCourseAssignments,
  useGradebook,
  useAssignmentAnalytics,
} from '../api/hooks'
import StatusBadge from '../components/StatusBadge'
import { buildCanvasCsv } from './gradebookExport'

/**
 * Gradebook and summary analytics for one assignment.
 *
 * Deliberately available while the assignment is still open -- the server does
 * not gate these on closure, so staff can watch a class work rather than only
 * read the post-mortem. Rows come from the roster, so a student who never
 * opened the assignment still appears; that absence is the useful signal.
 */

type Filter = 'all' | 'not_started' | 'in_progress' | 'submitted' | 'closed'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'not_started', label: 'Not started' },
  { key: 'in_progress', label: 'In progress' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'closed', label: 'Closed' },
]

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900 tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

function cellClass(status: string): string {
  if (status === 'correct') return 'bg-green-100 text-green-700'
  if (status === 'incorrect') return 'bg-red-100 text-red-700'
  return 'bg-gray-100 text-gray-400'
}

function cellGlyph(status: string): string {
  if (status === 'correct') return '✓'
  if (status === 'incorrect') return '✗'
  return '–'
}

export default function GradesTab({ courseId }: { courseId: string }) {
  const { data: assignments, isLoading: loadingList } = useCourseAssignments(courseId)
  const [selectedId, setSelectedId] = useState<string>('')
  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')

  const assignmentId = selectedId || (assignments?.[0]?.id ?? '')
  const { data: gradebook, isLoading: loadingBook } = useGradebook(assignmentId)
  const { data: analytics } = useAssignmentAnalytics(assignmentId)

  const counts = useMemo(() => {
    const base: Record<string, number> = {
      all: 0,
      not_started: 0,
      in_progress: 0,
      submitted: 0,
      closed: 0,
    }
    for (const row of gradebook?.rows ?? []) {
      base['all'] = (base['all'] ?? 0) + 1
      base[row.status] = (base[row.status] ?? 0) + 1
    }
    return base
  }, [gradebook])

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return (gradebook?.rows ?? []).filter((row) => {
      if (filter !== 'all' && row.status !== filter) return false
      if (!needle) return true
      return (
        row.displayName.toLowerCase().includes(needle) ||
        row.externalId.toLowerCase().includes(needle)
      )
    })
  }, [gradebook, filter, search])

  if (loadingList) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!assignments || assignments.length === 0) {
    return (
      <p className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
        No assignments yet. Create one on the Assignments tab to see grades here.
      </p>
    )
  }

  const total = gradebook?.totalPoints ?? 0

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <label htmlFor="grades-assignment" className="text-sm font-medium text-gray-700">
          Assignment
        </label>
        <select
          id="grades-assignment"
          value={assignmentId}
          onChange={(e) => {
            setSelectedId(e.target.value)
          }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          {assignments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
        <button
          disabled={!gradebook}
          onClick={() => {
            if (!gradebook) return
            const csv = buildCanvasCsv({ title: gradebook.title, rows: gradebook.rows })
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
            const url = URL.createObjectURL(blob)
            const a = Object.assign(document.createElement('a'), {
              href: url,
              download: `${gradebook.slug ?? gradebook.title}-grades.csv`,
            })
            a.click()
            URL.revokeObjectURL(url)
          }}
          className="ml-auto rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40"
        >
          Export CSV
        </button>
      </div>

      {analytics && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat
              label="Students"
              value={String(analytics.studentCount)}
              hint={`${analytics.startedCount} started`}
            />
            <Stat
              label="Completed"
              value={String(analytics.closedCount)}
              hint={`${analytics.submittedCount} hand-submitted`}
            />
            <Stat
              label="Average"
              value={
                analytics.meanScore === null
                  ? '—'
                  : `${analytics.meanScore.toFixed(2)} / ${analytics.totalPoints}`
              }
              hint={
                analytics.gradedCount > 0
                  ? `over ${analytics.gradedCount} graded`
                  : 'no final work yet'
              }
            />
            <Stat
              label="Median"
              value={analytics.medianScore === null ? '—' : analytics.medianScore.toFixed(2)}
            />
            <Stat
              label="Range"
              value={
                analytics.minScore === null || analytics.maxScore === null
                  ? '—'
                  : `${analytics.minScore}–${analytics.maxScore}`
              }
            />
          </div>

          <section className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Success rate by problem
            </h3>
            <div className="flex flex-col gap-2">
              {analytics.problems.map((p) => (
                <div key={p.index} className="flex items-center gap-3">
                  <span className="w-8 text-right text-xs text-gray-500">#{p.index}</span>
                  <div className="h-3 flex-1 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{ width: `${(p.successRate ?? 0) * 100}%` }}
                    />
                  </div>
                  <span className="w-32 text-xs tabular-nums text-gray-500">
                    {p.successRate === null
                      ? 'no attempts'
                      : `${Math.round(p.successRate * 100)}% of ${p.attemptedCount}`}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => {
              setFilter(f.key)
            }}
            className={[
              'rounded-full border px-3 py-1 text-xs font-medium',
              filter === f.key
                ? 'border-blue-600 bg-blue-50 text-blue-700'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50',
            ].join(' ')}
          >
            {f.label} ({counts[f.key] ?? 0})
          </button>
        ))}
        <input
          type="search"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
          }}
          placeholder="Search name or ID"
          aria-label="Search students"
          className="ml-auto rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      {loadingBook ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Student
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Score
                </th>
                {(gradebook?.problems ?? []).map((p) => (
                  <th
                    key={p.index}
                    className="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wide text-gray-500"
                    title={p.gradeable ? p.problemType : `${p.problemType} (not gradeable)`}
                  >
                    {p.index}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => (
                <tr key={row.externalId || row.displayName}>
                  <td className="px-4 py-2 text-sm">
                    <span className="font-medium text-gray-900">{row.displayName}</span>
                    <span className="ml-2 text-xs text-gray-400">{row.externalId}</span>
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="px-4 py-2 text-sm tabular-nums text-gray-700">
                    {/* Withheld until the work is final: a partial score shown
                        as a grade would misrepresent a student mid-assignment. */}
                    {row.earned === null ? (
                      <span className="text-gray-400">—</span>
                    ) : (
                      `${row.earned} / ${total}`
                    )}
                  </td>
                  {row.problems.map((cell) => (
                    <td key={cell.index} className="px-2 py-2 text-center">
                      <span
                        className={[
                          'inline-flex h-6 w-6 items-center justify-center rounded text-xs font-semibold',
                          cellClass(cell.status),
                        ].join(' ')}
                        title={`Problem ${cell.index}: ${cell.status} (${cell.attemptCount} attempt${cell.attemptCount === 1 ? '' : 's'})`}
                      >
                        {cellGlyph(cell.status)}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={3 + (gradebook?.problems.length ?? 0)}
                    className="px-4 py-8 text-center text-sm text-gray-500"
                  >
                    No students match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
