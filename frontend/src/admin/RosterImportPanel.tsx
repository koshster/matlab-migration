import { useMemo, useState } from 'react'
import { useAddRosterEntries } from '../api/hooks'
import type { RosterImportResult } from '../api/hooks'
import { parseRosterCsv } from './rosterCsv'

const PLACEHOLDER = `Paste a roster — one student per line. A header row is optional.

PID,Email,First Name,Last Name
A12345678,ada@ucsd.edu,Ada,Lovelace
A22222222,grace@ucsd.edu,Grace,Hopper

Bare PIDs or emails work too.`

const OUTCOME_LABEL: Record<string, string> = {
  added: 'Invited',
  already_present: 'Already on roster',
  linked_existing_account: 'Linked to existing account',
  invalid: 'Skipped',
}

const OUTCOME_STYLE: Record<string, string> = {
  added: 'text-green-700',
  already_present: 'text-gray-500',
  linked_existing_account: 'text-blue-700',
  invalid: 'text-red-700',
}

export default function RosterImportPanel({
  courseId,
  onClose,
}: {
  courseId: string
  onClose: () => void
}) {
  const [text, setText] = useState('')
  const [result, setResult] = useState<RosterImportResult | null>(null)
  const addMutation = useAddRosterEntries(courseId)

  // Parsed live so Marko sees what will be submitted before committing.
  const parsed = useMemo(() => parseRosterCsv(text), [text])

  function handleSubmit() {
    if (parsed.entries.length === 0) return
    addMutation.mutate(
      { entries: parsed.entries },
      { onSuccess: (data) => { setResult(data) } },
    )
  }

  if (result) {
    return (
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="font-semibold text-gray-900">Import complete</h3>
        <p className="mt-1 text-sm text-gray-600">
          {result.added} invited · {result.linked} linked to an existing account ·{' '}
          {result.alreadyPresent} already on the roster · {result.invalid} skipped
        </p>

        {result.results.length > 0 && (
          <div className="mt-3 max-h-64 overflow-y-auto rounded-md border border-gray-100">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-3 py-1.5 font-medium">Row</th>
                  <th className="px-3 py-1.5 font-medium">PID</th>
                  <th className="px-3 py-1.5 font-medium">Email</th>
                  <th className="px-3 py-1.5 font-medium">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {result.results.map((row) => (
                  <tr key={row.row}>
                    <td className="px-3 py-1.5 text-gray-400">{row.row}</td>
                    <td className="px-3 py-1.5 font-mono text-xs">{row.pid ?? '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600">{row.email ?? '—'}</td>
                    <td
                      className={[
                        'px-3 py-1.5 text-xs',
                        OUTCOME_STYLE[row.outcome] ?? 'text-gray-600',
                      ].join(' ')}
                    >
                      {OUTCOME_LABEL[row.outcome] ?? row.outcome}
                      {row.message ? ` — ${row.message}` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={() => {
              setResult(null)
              setText('')
            }}
            className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Add more
          </button>
          <button
            onClick={onClose}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Done
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="font-semibold text-gray-900">Add students</h3>
      <p className="mt-1 text-sm text-gray-500">
        Students who have not signed up yet can be added now — their assignments
        are reserved and appear once they register and accept.
      </p>

      <textarea
        value={text}
        onChange={(e) => { setText(e.target.value) }}
        placeholder={PLACEHOLDER}
        rows={10}
        aria-label="Roster to import"
        className="mt-3 w-full rounded-md border border-gray-300 p-3 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />

      {text.trim() !== '' && (
        <div className="mt-2 text-sm">
          <p className="text-gray-600">
            <strong>{parsed.entries.length}</strong>{' '}
            {parsed.entries.length === 1 ? 'student' : 'students'} ready to add
          </p>
          {parsed.skipped.length > 0 && (
            <details className="mt-1">
              <summary className="cursor-pointer text-amber-700">
                {parsed.skipped.length}{' '}
                {parsed.skipped.length === 1 ? 'line' : 'lines'} will be skipped
              </summary>
              <ul className="mt-1 flex flex-col gap-0.5 pl-4 text-xs text-gray-500">
                {parsed.skipped.map((s) => (
                  <li key={s.line}>
                    Line {s.line}: {s.reason} —{' '}
                    <span className="font-mono">{s.text}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {addMutation.isError && (
        <p className="mt-3 text-sm text-red-600">
          {addMutation.error.status === 403
            ? 'You do not have permission to change this roster.'
            : 'Could not add students. Try again.'}
        </p>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={parsed.entries.length === 0 || addMutation.isPending}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {addMutation.isPending
            ? 'Adding…'
            : `Add ${String(parsed.entries.length)} student${parsed.entries.length === 1 ? '' : 's'}`}
        </button>
      </div>
    </div>
  )
}
