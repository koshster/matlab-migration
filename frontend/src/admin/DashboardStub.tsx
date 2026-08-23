import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInstructor } from '../context/InstructorContext'
import { useSetInstructor } from '../context/InstructorContext'
import { useInstructorLogout, useInstructorMe } from '../api/hooks'

export default function DashboardStub() {
  const instructor = useInstructor()
  const setInstructor = useSetInstructor()
  const navigate = useNavigate()
  const logoutMutation = useInstructorLogout()

  // The context copy lives in sessionStorage and can outlive the httpOnly
  // cookie, so confirm the session against the server and drop it if the
  // cookie is gone. Without this the dashboard renders for a dead session.
  const { data, isError } = useInstructorMe()

  useEffect(() => {
    if (isError) {
      setInstructor(null)
      navigate('/admin/login', { replace: true })
      return
    }
    const fresh = data?.instructor
    if (fresh && (fresh.id !== instructor.id || fresh.name !== instructor.name)) {
      setInstructor(fresh)
    }
  }, [data, isError, instructor.id, instructor.name, navigate, setInstructor])

  function handleLogout() {
    logoutMutation.mutate(undefined, {
      onSettled: () => {
        setInstructor(null)
        navigate('/admin/login')
      },
    })
  }

  return (
    <main className="flex min-h-screen flex-col bg-gray-50">
      <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
        <span className="text-sm font-semibold text-gray-800">Statics Platform — Instructor</span>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{instructor.name}</span>
          <button
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
          >
            {logoutMutation.isPending ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Instructor Dashboard</h1>
          <p className="mt-2 text-sm text-gray-500">
            Welcome, {instructor.name}. The full dashboard is coming in Phase 6.
          </p>
        </div>
      </div>
    </main>
  )
}
