import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStudentSession } from '../api/hooks'
import { useSetSession } from '../context/SessionContext'

const DEMO_SLUG = 'truss-fall-2026'

export default function SessionGate() {
  const navigate = useNavigate()
  const setSession = useSetSession()
  const { mutate, isPending, isError } = useStudentSession()

  const [fields, setFields] = useState({ externalId: '', firstName: '', lastName: '' })

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFields((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    mutate(
      { ...fields, assignmentSlug: DEMO_SLUG },
      {
        onSuccess: (data) => {
          setSession({
            studentId: data.student.id,
            firstName: data.student.firstName,
            lastName: data.student.lastName,
            slug: DEMO_SLUG,
          })
          navigate(`/assignment/${DEMO_SLUG}`)
        },
        onError: (err) => {
          if (err.status === 409) {
            navigate(`/assignment/${DEMO_SLUG}/submitted`)
          }
        },
      },
    )
  }

  const disabled = isPending || !fields.externalId || !fields.firstName || !fields.lastName

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-md">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Statics Platform</h1>
        <p className="mb-6 text-sm text-gray-500">Enter your information to begin.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="externalId">
              Student ID (PID)
            </label>
            <input
              id="externalId"
              name="externalId"
              type="text"
              value={fields.externalId}
              onChange={handleChange}
              disabled={isPending}
              placeholder="A12345678"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="firstName">
              First Name
            </label>
            <input
              id="firstName"
              name="firstName"
              type="text"
              value={fields.firstName}
              onChange={handleChange}
              disabled={isPending}
              placeholder="Koshik"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="lastName">
              Last Name
            </label>
            <input
              id="lastName"
              name="lastName"
              type="text"
              value={fields.lastName}
              onChange={handleChange}
              disabled={isPending}
              placeholder="Kumar"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
              required
            />
          </div>

          {isError && (
            <p className="text-sm text-red-600">Something went wrong. Please try again.</p>
          )}

          <button
            type="submit"
            disabled={disabled}
            className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? 'Starting…' : 'Start Assignment'}
          </button>
        </form>
      </div>
    </main>
  )
}
