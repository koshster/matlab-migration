import type { components } from '@statics/contract/src/index'

type AnswerSchema = components['schemas']['AnswerSchema']

interface AnswerPanelProps {
  schema: AnswerSchema
  values: Record<string, number | null>
  perField: Record<string, boolean> | null
  onChange: (key: string, value: number | null) => void
  disabled?: boolean
}

function fieldRingClass(perField: Record<string, boolean> | null, key: string): string {
  if (perField === null) return 'border-gray-300'
  return perField[key] ? 'border-green-500 ring-1 ring-green-400' : 'border-red-500 ring-1 ring-red-400'
}

export default function AnswerPanel({ schema, values, perField, onChange, disabled }: AnswerPanelProps) {
  return (
    <div className="flex flex-col gap-5 overflow-y-auto p-4">
      {schema.groups.map((group) => (
        <section key={group.id}>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            {group.label}
          </h3>
          <div className="flex flex-col gap-2">
            {group.fields.map((field) => (
              <div key={field.key} className="flex items-center gap-2">
                <label
                  htmlFor={`field-${field.key}`}
                  className="w-8 text-right text-sm font-medium text-gray-700"
                >
                  {field.label}
                </label>
                <input
                  id={`field-${field.key}`}
                  type="number"
                  step="0.01"
                  value={values[field.key] ?? ''}
                  onChange={(e) => {
                    const raw = e.target.value
                    onChange(field.key, raw === '' ? null : parseFloat(raw))
                  }}
                  disabled={disabled}
                  className={[
                    'w-28 rounded-md border px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50',
                    fieldRingClass(perField, field.key),
                  ].join(' ')}
                />
                {field.unit && (
                  <span className="text-sm text-gray-400">{field.unit}</span>
                )}
                {perField !== null && (
                  <span className="text-sm">
                    {perField[field.key] ? '✓' : '✗'}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
