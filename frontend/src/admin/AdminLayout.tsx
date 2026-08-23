import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useInstructor, useSetInstructor } from '../context/InstructorContext'
import { useInstructorLogout, useInstructorMe } from '../api/hooks'

/**
 * Shared admin chrome. Also the single place the instructor session is
 * revalidated: the context copy lives in sessionStorage and can outlive the
 * httpOnly cookie, so every admin page confirms against the server.
 */
export default function AdminLayout({
  children,
  breadcrumb,
}: {
  children: React.ReactNode
  breadcrumb?: React.ReactNode
}) {
  const instructor = useInstructor()
  const setInstructor = useSetInstructor()
  const navigate = useNavigate()
  const logoutMutation = useInstructorLogout()
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
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6">
        <div className="flex items-center gap-3 text-sm">
          <Link to="/admin" className="font-semibold text-gray-800 hover:text-blue-700">
            Statics Platform — Instructor
          </Link>
          {breadcrumb && (
            <>
              <span className="text-gray-300" aria-hidden="true">
                /
              </span>
              {breadcrumb}
            </>
          )}
        </div>
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
      <main className="flex-1 px-6 py-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  )
}
