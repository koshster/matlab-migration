import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface Session {
  studentId: string
  firstName: string
  lastName: string
  slug: string
}

const SessionContext = createContext<Session | null>(null)

export function useSession(): Session {
  const s = useContext(SessionContext)
  if (!s) throw new Error('useSession must be used inside SessionProvider')
  return s
}

export function useOptionalSession(): Session | null {
  return useContext(SessionContext)
}

interface SessionProviderProps {
  children: ReactNode
}

export function SessionProvider({ children }: SessionProviderProps) {
  const [session, setSession] = useState<Session | null>(null)

  return (
    <SessionContext.Provider value={session}>
      <SetSessionContext.Provider value={setSession}>
        {children}
      </SetSessionContext.Provider>
    </SessionContext.Provider>
  )
}

const SetSessionContext = createContext<((s: Session) => void) | null>(null)

export function useSetSession(): (s: Session) => void {
  const fn = useContext(SetSessionContext)
  if (!fn) throw new Error('useSetSession must be used inside SessionProvider')
  return fn
}
