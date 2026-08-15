import { useParams } from 'react-router-dom'
import { useResult } from '../api/hooks'
import { useSession } from '../context/SessionContext'

const statusStyle: Record<string, string> = {
  correct:    'bg-green-100 text-green-800',
  incorrect:  'bg-red-100 text-red-800',
  no_attempt: 'bg-gray-100 text-gray-600',
}

const statusLabel: Record<string, string> = {
  correct:    'Correct',
  incorrect:  'Incorrect',
  no_attempt: 'No attempt',
}

export default function SubmittedScreen() {
  const { slug = '' } = useParams<{ slug: string }>()
  const session = useSession()
  const { data, isLoading } = useResult(slug)

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">
        Could not load results.
      </div>
    )
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-bold text-gray-900">Assignment Submitted</h1>
        <p className="mt-1 text-sm text-gray-500">
          {session.firstName} {session.lastName}
        </p>

        <div className="mt-6 flex items-center gap-4">
          <span className="text-5xl font-bold text-blue-600">
            {data.score.earned}/{data.score.total}
          </span>
          <span className="text-lg text-gray-500">problems correct</span>
        </div>

        <table className="mt-6 w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="pb-2 pr-4">Problem</th>
              <th className="pb-2 pr-4">Result</th>
              <th className="pb-2 text-right">Points</th>
            </tr>
          </thead>
          <tbody>
            {data.problems.map((p) => (
              <tr key={p.index} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-medium text-gray-700">Problem {p.index}</td>
                <td className="py-2 pr-4">
                  <span
                    className={[
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      statusStyle[p.status] ?? '',
                    ].join(' ')}
                  >
                    {statusLabel[p.status] ?? p.status}
                  </span>
                </td>
                <td className="py-2 text-right text-gray-700">{p.points}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="mt-6 text-center text-xs text-gray-400">
          Your instructor has your results. You may close this tab.
        </p>
      </div>
    </main>
  )
}
