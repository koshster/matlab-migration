import { useState } from 'react'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useStudentInvitations,
} from '../api/hooks'
import type { StudentInvitation } from '../api/hooks'

export default function InvitationList() {
  const { data: invitations, isLoading, isError } = useStudentInvitations()

  // Invitations are the exception, not the norm — stay silent when there are
  // none rather than showing an empty section above the assignment list.
  if (isLoading || isError || !invitations || invitations.length === 0) return null

  return (
    <section aria-labelledby="invitations-heading" className="mb-8">
      <h2 id="invitations-heading" className="mb-3 text-sm font-semibold text-gray-700">
        {invitations.length === 1
          ? 'You have a course invitation'
          : `You have ${String(invitations.length)} course invitations`}
      </h2>
      <ul className="flex flex-col gap-3">
        {invitations.map((invitation) => (
          <InvitationCard key={invitation.id} invitation={invitation} />
        ))}
      </ul>
    </section>
  )
}

function InvitationCard({ invitation }: { invitation: StudentInvitation }) {
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const [confirmingDecline, setConfirmingDecline] = useState(false)

  const busy = accept.isPending || decline.isPending
  const failed = accept.isError || decline.isError

  return (
    <li className="rounded-xl border border-blue-200 bg-blue-50 px-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-blue-700">
            Invitation
          </p>
          <p className="mt-0.5 font-semibold text-gray-900">
            {invitation.course.code}
            {invitation.course.title ? ` · ${invitation.course.title}` : ''}
          </p>
          <p className="text-sm text-gray-600">
            {invitation.course.term} · {invitation.instructorName}
          </p>
          {invitation.assignmentCount > 0 && (
            <p className="mt-1 text-xs text-gray-500">
              {invitation.assignmentCount}{' '}
              {invitation.assignmentCount === 1 ? 'assignment' : 'assignments'} waiting
            </p>
          )}
        </div>

        {confirmingDecline ? (
          <div className="flex flex-col items-end gap-2">
            <p className="text-sm text-gray-700">
              Decline {invitation.course.code}? Your instructor would need to invite
              you again.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => { setConfirmingDecline(false) }}
                disabled={busy}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-blue-100 disabled:opacity-50"
              >
                Keep it
              </button>
              <button
                onClick={() => { decline.mutate(invitation.id) }}
                disabled={busy}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {decline.isPending ? 'Declining…' : 'Yes, decline'}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => { setConfirmingDecline(true) }}
              disabled={busy}
              className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-blue-100 disabled:opacity-50"
            >
              Decline
            </button>
            <button
              onClick={() => { accept.mutate(invitation.id) }}
              disabled={busy}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {accept.isPending ? 'Joining…' : 'Accept'}
            </button>
          </div>
        )}
      </div>

      {failed && (
        <p className="mt-2 text-sm text-red-700">
          {(accept.error ?? decline.error)?.status === 404
            ? 'This invitation is no longer available. Refresh to see the latest.'
            : 'Something went wrong. Please try again.'}
        </p>
      )}
    </li>
  )
}
