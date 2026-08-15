import type { CheckResult } from '../api/hooks'

interface FeedbackPanelProps {
  result: CheckResult | null
}

export default function FeedbackPanel({ result }: FeedbackPanelProps) {
  if (!result) return null

  return (
    <div
      aria-live="polite"
      className={[
        'border-t px-6 py-3 text-sm',
        result.correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50',
      ].join(' ')}
    >
      <div className="flex items-start gap-2">
        <span
          className={[
            'mt-0.5 h-3 w-3 flex-shrink-0 rounded-full',
            result.correct ? 'bg-green-500' : 'bg-red-500',
          ].join(' ')}
          aria-hidden
        />
        <div className="flex-1">
          <p className={result.correct ? 'font-medium text-green-800' : 'font-medium text-red-800'}>
            {result.message}
          </p>
          {result.perField && (
            <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
              {Object.entries(result.perField).map(([key, correct]) => (
                <li
                  key={key}
                  className={correct ? 'text-green-700' : 'text-red-700'}
                >
                  {key}: {correct ? '✓ correct' : '✗ incorrect'}
                </li>
              ))}
            </ul>
          )}
        </div>
        <span className="text-xs text-gray-400">attempt {result.attemptCount}</span>
      </div>
    </div>
  )
}
