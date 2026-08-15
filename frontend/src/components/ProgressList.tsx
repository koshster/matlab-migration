import type { components } from '@statics/contract/src/index'

type ProblemSummary = components['schemas']['ProblemSummary']

interface ProgressListProps {
  problems: ProblemSummary[]
  currentIndex: number
  onNavigate: (index: number) => void
}

const statusStyle: Record<ProblemSummary['status'], string> = {
  correct:    'bg-green-500 text-white',
  incorrect:  'bg-red-500 text-white',
  no_attempt: 'bg-gray-200 text-gray-600',
}

const statusLabel: Record<ProblemSummary['status'], string> = {
  correct:    '✓',
  incorrect:  '✗',
  no_attempt: '—',
}

export default function ProgressList({ problems, currentIndex, onNavigate }: ProgressListProps) {
  return (
    <nav aria-label="Problem progress" className="flex flex-col gap-1 p-3">
      <p className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Problems
      </p>
      {problems.map((p) => (
        <button
          key={p.index}
          onClick={() => { onNavigate(p.index) }}
          className={[
            'flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
            currentIndex === p.index
              ? 'bg-blue-50 ring-2 ring-blue-500 ring-inset'
              : 'hover:bg-gray-100',
          ].join(' ')}
        >
          <span
            className={[
              'flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold',
              statusStyle[p.status],
            ].join(' ')}
          >
            {statusLabel[p.status]}
          </span>
          <span className="font-medium text-gray-700">Problem {p.index}</span>
          {p.attemptCount > 0 && (
            <span className="ml-auto text-xs text-gray-400">{p.attemptCount}×</span>
          )}
        </button>
      ))}
    </nav>
  )
}
