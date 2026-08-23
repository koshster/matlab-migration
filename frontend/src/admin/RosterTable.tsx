import { useMemo, useState } from 'react'
import { useRoster, useUpdateRosterEntry } from '../api/hooks'
import type { RosterEntry } from '../api/hooks'

type StatusFilter = 'all' | RosterEntry['status']

const STATUS_STYLE: Record<RosterEntry['status'], string> = {
  active: 'bg-green-100 text-green-800',
  invited: 'bg-amber-100 text-amber-800',
  declined: 'bg-red-100 text-red-800',
  dropped: 'bg-gray-100 text-gray-600',
}

const STATUS_LABEL: Record<RosterEntry['status'], string> = {
  active: 'Enrolled',
  invited: 'Invited',
  declined: 'Declined',
  dropped: 'Dropped',
}

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'active', label: 'Enrolled' },
  { key: 'invited', label: 'Invited' },
  { key: 'declined', label: 'Declined' },
  { key: 'dropped', label: 'Dropped' },
]

function displayName(entry: RosterEntry): string {
  const name = [entry.firstName, entry.lastName].filter(Boolean).join(' ')
  return name || '—'
}

export default function RosterTable({ courseId }: { courseId: string }) {
  const { data: roster, isLoading, isError } = useRoster(courseId)
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')

  const counts = useMemo(() => {
    const base: Record<StatusFilter, number> = {
      all: roster?.length ?? 0,
      active: 0,
      invited: 0,
      declined: 0,
      dropped: 0,
    }
    roster?.forEach((e) => {
      base[e.status] += 1
    })
    return base
  }, [roster])

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (roster ?? [])
      .filter((e) => filter === 'all' || e.status === filter)
      .filter((e) => {
        if (!term) return true
        const haystack = [e.pid, e.email, e.firstName, e.lastName]
          .join(' ')
          .toLowerCase()
        return haystack.includes(term)
      })
  }, [roster, filter, search])

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
        Could not load the roster. Check your connection and reload.
      </p>
    )
  }

  const unclaimed = (roster ?? []).filter((e) => !e.hasAccount).length

  return (
    <div>
      {unclaimed > 0 && (
        <p className="mb-4 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-900">
          <strong>{unclaimed}</strong>{' '}
          {unclaimed === 1 ? 'student has' : 'students have'} not created an account
          yet. Their assignments are already reserved — they will appear as soon as
          each student registers and accepts the invitation.
        </p>
      )}

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1" role="group" aria-label="Filter by status">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => { setFilter(f.key) }}
              aria-pressed={filter === f.key}
              className={[
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                filter === f.key
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100',
              ].join(' ')}
            >
              {f.label}
              <span className="ml-1.5 text-xs opacity-70">{counts[f.key]}</span>
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value) }}
          placeholder="Search name, PID or email"
          aria-label="Search roster"
          className="w-64 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            {counts.all === 0
              ? 'Nobody on the roster yet. Use “Add students” to paste one in.'
              : 'No roster entries match this filter.'}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-2 font-medium">Student</th>
                <th className="px-4 py-2 font-medium">PID</th>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Account</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((entry) => (
                <RosterRow key={entry.id} courseId={courseId} entry={entry} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function RosterRow({ courseId, entry }: { courseId: string; entry: RosterEntry }) {
  const updateMutation = useUpdateRosterEntry(courseId)

  function setStatus(status: RosterEntry['status']) {
    updateMutation.mutate({ entryId: entry.id, body: { status } })
  }

  return (
    <tr className={entry.status === 'dropped' ? 'text-gray-400' : ''}>
      <td className="px-4 py-2 font-medium">{displayName(entry)}</td>
      <td className="px-4 py-2 font-mono text-xs">{entry.pid ?? '—'}</td>
      <td className="px-4 py-2 text-gray-600">{entry.email ?? '—'}</td>
      <td className="px-4 py-2">
        <span
          className={[
            'rounded-full px-2 py-0.5 text-xs font-medium',
            STATUS_STYLE[entry.status],
          ].join(' ')}
        >
          {STATUS_LABEL[entry.status]}
        </span>
      </td>
      <td className="px-4 py-2">
        {entry.hasAccount ? (
          <span className="text-xs text-gray-500">Registered</span>
        ) : (
          <span className="text-xs text-amber-700">Not yet</span>
        )}
      </td>
      <td className="px-4 py-2 text-right">
        {entry.status === 'dropped' ? (
          <button
            onClick={() => { setStatus('invited') }}
            disabled={updateMutation.isPending}
            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
          >
            Restore
          </button>
        ) : (
          <button
            onClick={() => { setStatus('dropped') }}
            disabled={updateMutation.isPending}
            className="text-xs text-gray-500 hover:text-red-600 hover:underline disabled:opacity-50"
          >
            Drop
          </button>
        )}
      </td>
    </tr>
  )
}
