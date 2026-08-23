import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider, useOptionalSession } from './context/SessionContext'
import { InstructorProvider, useOptionalInstructor } from './context/InstructorContext'

const WorkspaceLayout = lazy(() => import('./components/WorkspaceLayout'))
const SubmittedScreen = lazy(() => import('./routes/SubmittedRoute'))
const StudentAuthPage = lazy(() => import('./student/AuthPage'))
const StudentDashboard = lazy(() => import('./student/Dashboard'))
const AdminAuthPage = lazy(() => import('./admin/AuthPage'))
const DashboardStub = lazy(() => import('./admin/DashboardStub'))

function RequireSession({ children }: { children: React.ReactNode }) {
  const session = useOptionalSession()
  if (!session) return <Navigate to="/student/login" replace />
  return <>{children}</>
}

function RequireInstructor({ children }: { children: React.ReactNode }) {
  const instructor = useOptionalInstructor()
  if (!instructor) return <Navigate to="/admin/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/student/login" replace />} />

      {/* Student routes */}
      <Route
        path="/student/login"
        element={
          <Suspense fallback={<FullPageSpinner />}>
            <StudentAuthPage />
          </Suspense>
        }
      />
      <Route
        path="/student/dashboard"
        element={
          <RequireSession>
            <Suspense fallback={<FullPageSpinner />}>
              <StudentDashboard />
            </Suspense>
          </RequireSession>
        }
      />
      <Route
        path="/assignment/:slug"
        element={
          <RequireSession>
            <Suspense fallback={<FullPageSpinner />}>
              <WorkspaceLayout />
            </Suspense>
          </RequireSession>
        }
      />
      <Route
        path="/assignment/:slug/submitted"
        element={
          <RequireSession>
            <Suspense fallback={<FullPageSpinner />}>
              <SubmittedScreen />
            </Suspense>
          </RequireSession>
        }
      />
      {/* Instructor routes */}
      <Route
        path="/admin/login"
        element={
          <Suspense fallback={<FullPageSpinner />}>
            <AdminAuthPage />
          </Suspense>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireInstructor>
            <Suspense fallback={<FullPageSpinner />}>
              <DashboardStub />
            </Suspense>
          </RequireInstructor>
        }
      />
      <Route path="/admin/*" element={<Navigate to="/admin/login" replace />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
    </div>
  )
}

export default function App() {
  return (
    <SessionProvider>
      <InstructorProvider>
        <AppRoutes />
      </InstructorProvider>
    </SessionProvider>
  )
}
