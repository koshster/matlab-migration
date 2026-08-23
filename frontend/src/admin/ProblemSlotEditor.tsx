import { useProblemTypes } from '../api/hooks'
import type { AdminProblemSlot, ParamFieldSpec, ProblemTypeInfo } from '../api/hooks'

/**
 * Difficulty ramps, expressed against whichever param the problem type nominates
 * as its first knob. Named after how an instructor thinks about a problem set
 * rather than after any particular problem type.
 */
const RAMPS: { label: string; values: number[] }[] = [
  { label: 'Standard (8)', values: [3, 3, 4, 4, 5, 5, 6, 6] },
  { label: 'Gentle (6)', values: [3, 3, 3, 4, 4, 4] },
  { label: 'Steep (8)', values: [4, 4, 5, 5, 6, 6, 7, 8] },
]

function defaultParams(info: ProblemTypeInfo): Record<string, number> {
  return Object.fromEntries(info.paramsSchema.map((f) => [f.name, f.default]))
}

export default function ProblemSlotEditor({
  problems,
  onChange,
  onPreview,
}: {
  problems: AdminProblemSlot[]
  onChange: (problems: AdminProblemSlot[]) => void
  onPreview?: (orderIndex: number) => void
}) {
  const { data: problemTypes, isLoading } = useProblemTypes()

  if (isLoading || !problemTypes || problemTypes.length === 0) {
    return <p className="text-sm text-gray-500">Loading problem types…</p>
  }

  // Hoisted `function` bodies below don't inherit the narrowing above.
  const types = problemTypes
  const infoFor = (type: string) =>
    types.find((t) => t.problemType === type) ?? types[0]

  // Renumber so orderIndex always matches position after any edit.
  const renumber = (slots: AdminProblemSlot[]) =>
    slots.map((s, i) => ({ ...s, orderIndex: i + 1 }))

  function addSlot() {
    const info = types[0]
    // Explicit length check rather than bare indexing: noUncheckedIndexedAccess
    // is off, so `problems[n]` is typed non-nullable even when the array is
    // empty — which it is for a brand-new assignment.
    const previous =
      problems.length > 0 ? problems[problems.length - 1] : undefined
    onChange(
      renumber([
        ...problems,
        {
          orderIndex: problems.length + 1,
          problemType: info.problemType,
          // Copy the previous slot's settings — consecutive problems are
          // usually variations on each other.
          params: previous ? { ...previous.params } : defaultParams(info),
          points: previous?.points ?? 1,
        },
      ]),
    )
  }

  function applyRamp(values: number[]) {
    const info = types[0]
    const rampKey = info.paramsSchema[0]?.name
    if (!rampKey) return
    onChange(
      renumber(
        values.map((value, i) => ({
          orderIndex: i + 1,
          problemType: info.problemType,
          params: { ...defaultParams(info), [rampKey]: value },
          points: i < problems.length ? problems[i].points : 1,
        })),
      ),
    )
  }

  function updateSlot(index: number, patch: Partial<AdminProblemSlot>) {
    onChange(renumber(problems.map((s, i) => (i === index ? { ...s, ...patch } : s))))
  }

  function move(index: number, delta: number) {
    const target = index + delta
    if (target < 0 || target >= problems.length) return
    const next = [...problems]
    const [moved] = next.splice(index, 1)
    next.splice(target, 0, moved)
    onChange(renumber(next))
  }

  const rampKey = types[0].paramsSchema[0]?.name

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-500">Presets:</span>
        {RAMPS.map((ramp) => (
          <button
            key={ramp.label}
            type="button"
            onClick={() => { applyRamp(ramp.values) }}
            className="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700"
          >
            {ramp.label}
          </button>
        ))}
        {rampKey && (
          <span className="text-xs text-gray-400">
            (sets “{types[0].paramsSchema[0].label}” per problem)
          </span>
        )}
      </div>

      {problems.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
          <p className="text-sm text-gray-500">
            No problems yet. Pick a preset above or add one at a time.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {problems.map((slotSpec, i) => (
            <li
              key={slotSpec.orderIndex}
              className="rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="flex flex-wrap items-end gap-3">
                <span className="w-6 shrink-0 text-sm font-semibold text-gray-400">
                  {slotSpec.orderIndex}
                </span>

                {types.length > 1 ? (
                  <label className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-gray-600">Type</span>
                    <select
                      value={slotSpec.problemType}
                      onChange={(e) => {
                        const info = infoFor(e.target.value)
                        updateSlot(i, {
                          problemType: info.problemType,
                          params: defaultParams(info),
                        })
                      }}
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                    >
                      {types.map((t) => (
                        <option key={t.problemType} value={t.problemType}>
                          {t.displayName}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <span className="pb-1 text-xs text-gray-500">
                    {infoFor(slotSpec.problemType).displayName}
                  </span>
                )}

                {infoFor(slotSpec.problemType).paramsSchema.map((field) => (
                  <ParamInput
                    key={field.name}
                    field={field}
                    value={slotSpec.params[field.name] ?? field.default}
                    onChange={(value) => {
                      updateSlot(i, { params: { ...slotSpec.params, [field.name]: value } })
                    }}
                  />
                ))}

                <label className="flex w-20 flex-col gap-1">
                  <span className="text-xs font-medium text-gray-600">Points</span>
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    value={slotSpec.points}
                    onChange={(e) => { updateSlot(i, { points: Number(e.target.value) }) }}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                  />
                </label>

                <div className="ml-auto flex items-center gap-1">
                  {onPreview && (
                    <button
                      type="button"
                      onClick={() => { onPreview(slotSpec.orderIndex) }}
                      className="rounded-md px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
                    >
                      Preview
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => { move(i, -1) }}
                    disabled={i === 0}
                    aria-label={`Move problem ${String(slotSpec.orderIndex)} up`}
                    className="rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => { move(i, 1) }}
                    disabled={i === problems.length - 1}
                    aria-label={`Move problem ${String(slotSpec.orderIndex)} down`}
                    className="rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 disabled:opacity-30"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(renumber(problems.filter((_, idx) => idx !== i)))
                    }}
                    aria-label={`Remove problem ${String(slotSpec.orderIndex)}`}
                    className="rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-red-50 hover:text-red-600"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          onClick={addSlot}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700"
        >
          Add problem
        </button>
        {problems.length > 0 && (
          <span className="text-xs text-gray-500">
            {problems.length} problems ·{' '}
            {problems.reduce((sum, s) => sum + s.points, 0)} points total
          </span>
        )}
      </div>
    </div>
  )
}

function ParamInput({
  field,
  value,
  onChange,
}: {
  field: ParamFieldSpec
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="flex w-28 flex-col gap-1">
      <span className="text-xs font-medium text-gray-600" title={field.helpText}>
        {field.label}
      </span>
      <input
        type="number"
        value={value}
        min={field.minimum ?? undefined}
        max={field.maximum ?? undefined}
        step={field.step ?? (field.valueType === 'integer' ? 1 : 'any')}
        aria-label={field.label}
        onChange={(e) => { onChange(Number(e.target.value)) }}
        className="rounded-md border border-gray-300 px-2 py-1 text-sm"
      />
    </label>
  )
}
