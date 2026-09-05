interface ActionBarProps {
  onPrev: () => void
  onNext: () => void
  onCheck: () => void
  onSave: () => void
  onSubmit: () => void
  /** The whole assignment is final: hide the actions rather than dead-disable them. */
  reviewMode: boolean
  /** This problem alone is read-only (already correct, or unavailable). */
  problemLocked: boolean
  checking: boolean
  saveStatus: 'idle' | 'saving' | 'saved'
}

export default function ActionBar({
  onPrev,
  onNext,
  onCheck,
  onSave,
  onSubmit,
  reviewMode,
  problemLocked,
  checking,
  saveStatus,
}: ActionBarProps) {
  const saveLabel =
    saveStatus === 'saving' ? 'Saving…' : saveStatus === 'saved' ? 'Saved ✓' : 'Save Progress'

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-6 py-3">
      {/* Navigation stays live in review mode -- that is the whole point of it. */}
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

      <div className="flex items-center gap-2">
        {reviewMode ? (
          <span className="text-sm text-gray-500">Review only — this assignment is closed.</span>
        ) : (
          <>
            <button
              onClick={onSave}
              disabled={problemLocked || saveStatus === 'saving'}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              {saveLabel}
            </button>
            <button
              onClick={onCheck}
              disabled={problemLocked || checking}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              {checking ? 'Checking…' : 'Check Answer'}
            </button>
            <button
              onClick={onSubmit}
              className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              Submit
            </button>
          </>
        )}
      </div>
    </div>
  )
}
