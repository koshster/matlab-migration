import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface InstructorSession {
  id: string
  email: string
  name: string
}

const STORAGE_KEY = 'instructor_session'

const InstructorContext = createContext<InstructorSession | null>(null)
const SetInstructorContext = createContext<((s: InstructorSession | null) => void) | null>(null)

export function useInstructor(): InstructorSession {
  const s = useContext(InstructorContext)
  if (!s) throw new Error('useInstructor must be used inside InstructorProvider')
  return s
}

export function useOptionalInstructor(): InstructorSession | null {
  return useContext(InstructorContext)
}

export function useSetInstructor(): (s: InstructorSession | null) => void {
  const fn = useContext(SetInstructorContext)
  if (!fn) throw new Error('useSetInstructor must be used inside InstructorProvider')
  return fn
}

export function InstructorProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<InstructorSession | null>(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as InstructorSession) : null
    } catch {
      return null
    }
  })

  function setSession(s: InstructorSession | null) {
    if (s === null) {
      sessionStorage.removeItem(STORAGE_KEY)
    } else {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    }
    setSessionState(s)
  }

  return (
    <InstructorContext.Provider value={session}>
      <SetInstructorContext.Provider value={setSession}>
        {children}
      </SetInstructorContext.Provider>
    </InstructorContext.Provider>
  )
}
