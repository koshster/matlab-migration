import type { components } from '@statics/contract/src/index'

type AnswerSchema = components['schemas']['AnswerSchema']

interface AnswerPanelProps {
  schema: AnswerSchema
  values: Record<string, number | null>
  perField: Record<string, boolean> | null
  onChange: (key: string, value: number | null) => void
  /** Read-only: render values as text rather than as dead input boxes. */
  readOnly?: boolean
  /** Reference answers, present only when the server chose to reveal them. */
  correctAnswers?: Record<string, number> | null
}

function fieldRingClass(perField: Record<string, boolean> | null, key: string): string {
  // A key missing from perField means "not graded", not "wrong". Painting it
  // red would tell a student their answer failed when it was never checked.
  if (perField === null || !(key in perField)) return 'border-gray-300'
  return perField[key]
    ? 'border-green-500 ring-1 ring-green-400'
    : 'border-red-500 ring-1 ring-red-400'
}

function formatValue(value: number | null | undefined, decimals: number | null): string {
  if (value === null || value === undefined) return '—'
  return decimals === null ? String(value) : value.toFixed(decimals)
}

export default function AnswerPanel({
  schema,
  values,
  perField,
  onChange,
  readOnly,
  correctAnswers,
}: AnswerPanelProps) {
  const showSolutions = !!correctAnswers

  return (
    <div className="flex flex-col gap-5 overflow-y-auto p-4">
      {schema.groups.map((group) => (
        <section key={group.id}>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            {group.label}
          </h3>
          {showSolutions && (
            <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-gray-400">
              <span className="w-8" />
              <span className="w-20">Yours</span>
              <span>Correct</span>
            </div>
          )}
          <div className="flex flex-col gap-2">
            {group.fields.map((field) => (
              <div key={field.key} className="flex items-center gap-2">
                <label
                  htmlFor={`field-${field.key}`}
                  className="w-8 text-right text-sm font-medium text-gray-700"
                >
                  {field.label}
                </label>

                {readOnly ? (
                  // Static text, not a disabled input: a disabled field at
                  // opacity-50 is hard to read and is skipped by screen readers,
                  // which is the wrong trade for a review screen.
                  <output
                    id={`field-${field.key}`}
                    className={[
                      'w-20 rounded-md border bg-gray-50 px-2 py-1.5 text-sm tabular-nums text-gray-800',
                      fieldRingClass(perField, field.key),
                    ].join(' ')}
                  >
                    {formatValue(values[field.key], field.decimals)}
                  </output>
                ) : (
                  <input
                    id={`field-${field.key}`}
                    type="number"
                    step="0.01"
                    value={values[field.key] ?? ''}
                    onChange={(e) => {
                      const raw = e.target.value
                      onChange(field.key, raw === '' ? null : parseFloat(raw))
                    }}
                    className={[
                      'w-28 rounded-md border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400',
                      fieldRingClass(perField, field.key),
                    ].join(' ')}
                  />
                )}

                {showSolutions && (
                  <span className="text-sm font-medium tabular-nums text-green-700">
                    {formatValue(correctAnswers[field.key], field.decimals)}
                  </span>
                )}

                {field.unit && !showSolutions && (
                  <span className="text-sm text-gray-400">{field.unit}</span>
                )}

                {perField !== null && field.key in perField && (
                  <span className="text-sm">{perField[field.key] ? '✓' : '✗'}</span>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
