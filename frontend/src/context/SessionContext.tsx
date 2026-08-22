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

const STORAGE_KEY = 'statics_session'

export function SessionProvider({ children }: SessionProviderProps) {
  const [session, setSessionState] = useState<Session | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as Session) : null
    } catch {
      return null
    }
  })

  function setSession(s: Session | null) {
    if (s === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    }
    setSessionState(s)
  }

  return (
    <SessionContext.Provider value={session}>
      <SetSessionContext.Provider value={setSession}>
        {children}
      </SetSessionContext.Provider>
    </SessionContext.Provider>
  )
}

const SetSessionContext = createContext<((s: Session | null) => void) | null>(null)

export function useSetSession(): (s: Session | null) => void {
  const fn = useContext(SetSessionContext)
  if (!fn) throw new Error('useSetSession must be used inside SessionProvider')
  return fn
}
