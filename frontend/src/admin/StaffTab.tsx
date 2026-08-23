import { useState } from 'react'
import { useAddCourseStaff, useCourseStaff } from '../api/hooks'
import type { CourseRole } from '../api/hooks'

const ROLE_DESCRIPTION: Record<CourseRole, string> = {
  owner: 'Full control, including course staff',
  instructor: 'Manage roster and assignments',
  ta: 'View grades and drill into student work',
  reader: 'Read-only access',
}

const ASSIGNABLE: CourseRole[] = ['instructor', 'ta', 'reader']

export default function StaffTab({
  courseId,
  canManage,
}: {
  courseId: string
  canManage: boolean
}) {
  const { data: staff, isLoading, isError } = useCourseStaff(courseId)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<CourseRole>('ta')
  const addMutation = useAddCourseStaff(courseId)

  function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    addMutation.mutate({ email, role }, { onSuccess: () => { setEmail('') } })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">
        Could not load course staff.
      </p>
    )
  }

  return (
    <div>
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(staff ?? []).map((member) => (
              <tr key={member.id}>
                <td className="px-4 py-2 font-medium">{member.name}</td>
                <td className="px-4 py-2 text-gray-600">{member.email}</td>
                <td className="px-4 py-2">
                  <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                    {member.role}
                  </span>
                  <span className="ml-2 text-xs text-gray-400">
                    {ROLE_DESCRIPTION[member.role]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canManage ? (
        <form
          onSubmit={handleAdd}
          className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4"
        >
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">
              Add staff by email
            </span>
            <input
              value={email}
              onChange={(e) => { setEmail(e.target.value) }}
              placeholder="ta@ucsd.edu"
              type="email"
              required
              className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Role</span>
            <select
              value={role}
              onChange={(e) => { setRole(e.target.value as CourseRole) }}
              className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {ASSIGNABLE.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={addMutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {addMutation.isPending ? 'Adding…' : 'Add'}
          </button>

          {addMutation.isError && (
            <p className="w-full text-sm text-red-600">
              {addMutation.error.status === 404
                ? 'No instructor account with that email. They need to register first.'
                : addMutation.error.status === 409
                  ? 'That person already has a role on this course.'
                  : 'Could not add them. Try again.'}
            </p>
          )}
        </form>
      ) : (
        <p className="mt-4 text-sm text-gray-500">
          Only a course owner can change staff.
        </p>
      )}
    </div>
  )
}
