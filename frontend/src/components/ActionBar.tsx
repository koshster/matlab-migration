interface ActionBarProps {
  onPrev: () => void
  onNext: () => void
  onCheck: () => void
  onSave: () => void
  onSubmit: () => void
  locked: boolean
  checking: boolean
  saveStatus: 'idle' | 'saving' | 'saved'
}

export default function ActionBar({
  onPrev,
  onNext,
  onCheck,
  onSave,
  onSubmit,
  locked,
  checking,
  saveStatus,
}: ActionBarProps) {
  const saveLabel =
    saveStatus === 'saving' ? 'Saving…' : saveStatus === 'saved' ? 'Saved ✓' : 'Save Progress'

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-6 py-3">
      {/* Navigation */}
      <div className="flex gap-2">
        <button
          onClick={onPrev}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
        >
          ← Previous
        </button>
        <button
          onClick={onNext}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
        >
          Next →
        </button>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onSave}
          disabled={locked || saveStatus === 'saving'}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
        >
          {saveLabel}
        </button>
        <button
          onClick={onCheck}
          disabled={locked || checking}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
        >
          {checking ? 'Checking…' : 'Check Answer'}
        </button>
        <button
          onClick={onSubmit}
          disabled={locked}
          className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
        >
          Submit
        </button>
      </div>
    </div>
  )
}
