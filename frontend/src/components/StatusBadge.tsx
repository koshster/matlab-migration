/**
 * One badge vocabulary for assignment and problem status.
 *
 * These maps were hand-rolled in five places (student dashboard, submitted
 * screen, progress list, roster table, admin assignments tab). Adding the
 * `closed` status meant either editing all five or extracting this.
 */

type BadgeSpec = { label: string; className: string }

const assignmentStyles: Record<string, BadgeSpec | undefined> = {
  not_started: { label: 'Not started', className: 'bg-gray-100 text-gray-600' },
  in_progress: { label: 'In progress', className: 'bg-blue-100 text-blue-700' },
  submitted: { label: 'Submitted', className: 'bg-green-100 text-green-700' },
  // Final, but nobody pressed Submit -- the deadline did it.
  closed: { label: 'Closed', className: 'bg-amber-100 text-amber-800' },
}

const problemStyles: Record<string, BadgeSpec | undefined> = {
  no_attempt: { label: 'Not attempted', className: 'bg-gray-100 text-gray-500' },
  incorrect: { label: 'Incorrect', className: 'bg-red-100 text-red-700' },
  correct: { label: 'Correct', className: 'bg-green-100 text-green-700' },
}

interface StatusBadgeProps {
  status: string
  kind?: 'assignment' | 'problem'
  className?: string
}

export function statusLabel(status: string, kind: 'assignment' | 'problem' = 'assignment'): string {
  const table = kind === 'problem' ? problemStyles : assignmentStyles
  return table[status]?.label ?? status
}

export default function StatusBadge({ status, kind = 'assignment', className }: StatusBadgeProps) {
  const table = kind === 'problem' ? problemStyles : assignmentStyles
  const entry = table[status] ?? { label: status, className: 'bg-gray-100 text-gray-600' }
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        entry.className,
        className ?? '',
      ].join(' ')}
    >
      {entry.label}
    </span>
  )
}
