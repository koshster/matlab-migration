import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider, useOptionalSession } from './context/SessionContext'
import SessionGate from './components/SessionGate'

const WorkspaceLayout = lazy(() => import('./components/WorkspaceLayout'))
const SubmittedScreen = lazy(() => import('./routes/SubmittedRoute'))

function RequireSession({ children }: { children: React.ReactNode }) {
  const session = useOptionalSession()
  if (!session) return <Navigate to="/" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SessionGate />} />
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
      <AppRoutes />
    </SessionProvider>
  )
}
