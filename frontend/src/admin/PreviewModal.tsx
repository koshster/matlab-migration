import { Suspense, useState } from 'react'
import { useAssignmentPreview } from '../api/hooks'
import { getRenderer } from '../problems/registry'

/**
 * Renders a problem slot exactly as a student would see it.
 *
 * Uses the shared renderer registry, so this component has no knowledge of any
 * particular problem type — adding one needs no change here (CLAUDE.md).
 */
export default function PreviewModal({
  assignmentId,
  index,
  onClose,
}: {
  assignmentId: string
  index: number
  onClose: () => void
}) {
  const [seed, setSeed] = useState(1)
  const { data: problem, isLoading, isError } = useAssignmentPreview(assignmentId, index, seed)

  const Renderer = problem ? getRenderer(problem.problemType) : null

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`Preview of problem ${String(index)}`}
    >
      <div className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-xl bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
          <div>
            <h2 className="font-semibold text-gray-900">Problem {index} preview</h2>
            <p className="text-xs text-gray-500">
              What a student sees. Each student gets their own seed.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setSeed((s) => s + 1) }}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700"
            >
              Reroll
            </button>
            <button
              onClick={onClose}
              className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
            >
              Close
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {isLoading && (
            <div className="flex justify-center py-16">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
            </div>
          )}

          {isError && (
            <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">
              Could not generate a preview for this problem.
            </p>
          )}

          {problem && (
            <>
              <p className="mb-1 font-medium text-gray-900">{problem.prompt.title}</p>
              <p className="mb-4 text-sm text-gray-600">{problem.prompt.body}</p>

              <div className="mx-auto h-72 w-full max-w-xl">
                <Suspense
                  fallback={
                    <div className="flex h-full items-center justify-center text-gray-400">
                      Loading diagram…
                    </div>
                  }
                >
                  {Renderer && <Renderer geometry={problem.geometry} />}
                </Suspense>
              </div>

              <div className="mt-4 border-t border-gray-100 pt-3">
                <p className="mb-1 text-xs font-medium text-gray-500">
                  Students will be asked for:
                </p>
                <p className="text-sm text-gray-700">
                  {problem.answerSchema.groups
                    .flatMap((g) => g.fields.map((f) => f.label))
                    .join(', ')}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
