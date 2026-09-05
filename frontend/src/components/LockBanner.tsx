/**
 * Explains why the workspace is read-only.
 *
 * Previously the only signal was that the inputs were disabled and a "Submitted"
 * pill appeared in the header, which does not distinguish "you submitted this"
 * from "the deadline passed" and says nothing about a single locked problem.
 */

interface LockBannerProps {
  /** Assignment-level reason, null while the assignment is still open. */
  assignmentLockReason: 'submitted' | 'past_due' | null
  /** Problem-level reason for the problem currently on screen. */
  problemLockReason: 'correct' | 'submitted' | 'past_due' | 'unavailable' | null
  closesAt: string | null
  showingSolutions: boolean
}

function formatWhen(iso: string | null): string {
  if (!iso) return ''
  const when = new Date(iso)
  if (Number.isNaN(when.getTime())) return ''
  return when.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function LockBanner({
  assignmentLockReason,
  problemLockReason,
  closesAt,
  showingSolutions,
}: LockBannerProps) {
  let tone = 'bg-amber-50 text-amber-900 border-amber-200'
  let message: string

  if (assignmentLockReason === 'submitted') {
    message = 'You submitted this assignment. Your answers are shown for review and cannot be changed.'
  } else if (assignmentLockReason === 'past_due') {
    const when = formatWhen(closesAt)
    message = when
      ? `This assignment closed on ${when}. Your answers are shown for review and cannot be changed.`
      : 'This assignment is closed. Your answers are shown for review and cannot be changed.'
  } else if (problemLockReason === 'correct') {
    tone = 'bg-green-50 text-green-900 border-green-200'
    message = 'You answered this one correctly, so it is locked. The other problems are still open.'
  } else if (problemLockReason === 'unavailable') {
    tone = 'bg-gray-50 text-gray-700 border-gray-200'
    message = 'This problem type is not available yet, so it cannot be answered.'
  } else {
    return null
  }

  return (
    <div className={['border-b px-4 py-2 text-sm lg:px-6', tone].join(' ')} role="status">
      {message}
      {showingSolutions && ' The correct answers are shown beside your own.'}
    </div>
  )
}
