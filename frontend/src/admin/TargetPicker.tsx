import { useRoster } from '../api/hooks'
import type { AdminAssignmentDetail, RosterEntry } from '../api/hooks'

type Audience = AdminAssignmentDetail['audience']

function label(entry: RosterEntry): string {
  const name = [entry.firstName, entry.lastName].filter(Boolean).join(' ')
  return name || entry.pid || entry.email || 'Unnamed'
}

export default function TargetPicker({
  courseId,
  audience,
  targetEntryIds,
  onChange,
}: {
  courseId: string
  audience: Audience
  targetEntryIds: string[]
  onChange: (next: { audience: Audience; targetEntryIds: string[] }) => void
}) {
  const { data: roster } = useRoster(courseId)

  // Dropped and declined students cannot be assigned work.
  const assignable = (roster ?? []).filter(
    (e) => e.status === 'active' || e.status === 'invited',
  )
  const selected = new Set(targetEntryIds)

  function toggle(entryId: string) {
    const next = new Set(selected)
    if (next.has(entryId)) next.delete(entryId)
    else next.add(entryId)
    onChange({ audience: 'selected', targetEntryIds: [...next] })
  }

  return (
    <fieldset>
      <legend className="mb-2 text-xs font-medium text-gray-600">Assign to</legend>

      <div className="flex flex-col gap-2">
        <label className="flex items-start gap-2">
          <input
            type="radio"
            name="audience"
            checked={audience === 'all'}
            onChange={() => { onChange({ audience: 'all', targetEntryIds }) }}
            className="mt-1"
          />
          <span className="text-sm">
            <span className="font-medium text-gray-800">Everyone in this course</span>
            <span className="block text-xs text-gray-500">
              Including students who join later — no need to re-assign.
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2">
          <input
            type="radio"
            name="audience"
            checked={audience === 'selected'}
            onChange={() => { onChange({ audience: 'selected', targetEntryIds }) }}
            className="mt-1"
          />
          <span className="text-sm">
            <span className="font-medium text-gray-800">Specific students</span>
            <span className="block text-xs text-gray-500">
              {selected.size} of {assignable.length} selected
            </span>
          </span>
        </label>
      </div>

      {audience === 'selected' && (
        <div className="mt-3 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
            <span className="text-xs text-gray-500">
              Students not yet registered can still be selected.
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  onChange({
                    audience: 'selected',
                    targetEntryIds: assignable.map((e) => e.id),
                  })
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                Select all
              </button>
              <button
                type="button"
                onClick={() => { onChange({ audience: 'selected', targetEntryIds: [] }) }}
                className="text-xs text-gray-500 hover:underline"
              >
                Clear
              </button>
            </div>
          </div>
          <ul className="max-h-56 overflow-y-auto p-2">
            {assignable.length === 0 && (
              <li className="px-1 py-2 text-sm text-gray-500">
                Nobody on the roster yet.
              </li>
            )}
            {assignable.map((entry) => (
              <li key={entry.id}>
                <label className="flex items-center gap-2 rounded px-1 py-1 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selected.has(entry.id)}
                    onChange={() => { toggle(entry.id) }}
                  />
                  <span className="text-sm text-gray-800">{label(entry)}</span>
                  {entry.pid && (
                    <span className="font-mono text-xs text-gray-400">{entry.pid}</span>
                  )}
                  {!entry.hasAccount && (
                    <span className="ml-auto text-xs text-amber-700">not registered</span>
                  )}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}
    </fieldset>
  )
}
