import { Suspense, useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext'
import { useAssignment, useProblem, useSaveAnswers, useCheckAnswers, useSubmit } from '../api/hooks'
import type { CheckResult } from '../api/hooks'
import { getRenderer } from '../problems/registry'
import ProgressList from './ProgressList'
import InstructionPanel from './InstructionPanel'
import AnswerPanel from './AnswerPanel'
import FeedbackPanel from './FeedbackPanel'
import ActionBar from './ActionBar'
import LockBanner from './LockBanner'
import StatusBadge from './StatusBadge'

export default function WorkspaceLayout() {
  const { slug = '' } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const session = useSession()

  // 1-based, matching the contract's problem index.
  const [currentIndex, setCurrentIndex] = useState(1)
  const [answers, setAnswers] = useState<Record<string, number | null>>({})
  const [lastCheck, setLastCheck] = useState<CheckResult | null>(null)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  const { data: assignment } = useAssignment(slug)
  const { data: problem, isLoading: problemLoading, isError: problemError } = useProblem(slug, currentIndex)
  const saveMutation = useSaveAnswers(slug, currentIndex)
  const checkMutation = useCheckAnswers(slug, currentIndex)
  const submitMutation = useSubmit(slug)

  // Assignment-level: submitted or past its deadline. Problem-level: that,
  // or this particular problem was already answered correctly.
  const reviewMode = assignment?.locked ?? false
  const problemLocked = problem?.locked ?? reviewMode
  const correctAnswers = problem?.correctAnswers ?? null
  const totalProblems = assignment?.problemCount ?? 0

  // Hydrate saved answers once per problem.
  //
  // This used to key on the identity of `problem.savedAnswers`, so any
  // background refetch (the query goes stale after 30s, so a window refocus is
  // enough) handed back a fresh object and silently wiped whatever the student
  // had typed since. Keying on the index and tracking what we last hydrated
  // means a refetch of the same problem leaves in-flight edits alone.
  const hydratedFor = useRef<number | null>(null)
  useEffect(() => {
    if (!problem) return
    if (hydratedFor.current === problem.index) return
    hydratedFor.current = problem.index
    setAnswers(problem.savedAnswers)
    setLastCheck(null)
    setIsDirty(false)
  }, [problem])

  // Warn on browser tab close/refresh when there are unsaved changes
  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault() }
    window.addEventListener('beforeunload', handler)
    return () => { window.removeEventListener('beforeunload', handler) }
  }, [isDirty])

  const confirmLeave = useCallback(() => {
    if (!isDirty || reviewMode) return true
    return window.confirm('You have unsaved answers. Leave without saving?')
  }, [isDirty, reviewMode])

  function navigate_problem(index: number) {
    if (totalProblems < 1) return
    if (!confirmLeave()) return
    const next = ((((index - 1) % totalProblems) + totalProblems) % totalProblems) + 1
    setCurrentIndex(next)
  }

  function handleBack() {
    if (!confirmLeave()) return
    navigate('/student/dashboard')
  }

  function handleCheck() {
    checkMutation.mutate(
      { answers },
      {
        onSuccess: (result) => { setLastCheck(result) },
      },
    )
  }

  function handleSave() {
    setSaveStatus('saving')
    saveMutation.mutate(
      { answers },
      {
        onSuccess: () => {
          setSaveStatus('saved')
          setIsDirty(false)
          setTimeout(() => { setSaveStatus('idle') }, 2000)
        },
        onError: () => { setSaveStatus('idle') },
      },
    )
  }

  function handleSubmit() {
    if (!window.confirm('Submit your assignment? You cannot make changes after submitting.')) return
    submitMutation.mutate(undefined, {
      onSuccess: () => { navigate(`/assignment/${slug}/submitted`) },
    })
  }

  const DiagramRenderer = problem ? getRenderer(problem.problemType) : null

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => { setSidebarOpen(false) }}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-30 w-56 flex-shrink-0 overflow-y-auto border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0 lg:z-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Problem navigation"
      >
        <ProgressList
          problems={assignment?.problems ?? []}
          currentIndex={currentIndex}
          onNavigate={(i) => { navigate_problem(i); setSidebarOpen(false) }}
        />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 lg:hidden"
              onClick={() => { setSidebarOpen((o) => !o) }}
              aria-label="Toggle problem list"
              aria-expanded={sidebarOpen}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <rect y="3" width="20" height="2" rx="1" />
                <rect y="9" width="20" height="2" rx="1" />
                <rect y="15" width="20" height="2" rx="1" />
              </svg>
            </button>
            <button
              onClick={handleBack}
              className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
              aria-label="Back to assignments"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              My Assignments
            </button>
            <span className="hidden text-gray-300 lg:inline">|</span>
            <div className="hidden lg:block">
              <span className="text-sm text-gray-500">
                {session.firstName} {session.lastName}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {saveStatus === 'saved' && (
              <span className="text-xs text-green-600">Saved ✓</span>
            )}
            {reviewMode && (
              <StatusBadge
                status={assignment?.lockReason === 'submitted' ? 'submitted' : 'closed'}
              />
            )}
            <span className="text-sm font-medium text-gray-600">
              {assignment?.title ?? ''}
            </span>
          </div>
        </header>

        {/* Problem area */}
        <div className="flex flex-1 overflow-hidden">
          {problemError ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-500">
              <p className="text-sm">Failed to load problem. Check your connection.</p>
              <button
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                onClick={() => { window.location.reload() }}
              >
                Reload
              </button>
            </div>
          ) : problemLoading || !problem ? (
            <div className="flex flex-1 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
            </div>
          ) : (
            <div className="flex flex-1 flex-col overflow-hidden">
              <LockBanner
                assignmentLockReason={assignment?.lockReason ?? null}
                problemLockReason={problem.lockReason}
                closesAt={assignment?.closesAt ?? null}
                showingSolutions={!!correctAnswers}
              />
              <InstructionPanel prompt={problem.prompt} />

              <div className="flex flex-1 overflow-hidden">
                {/* Diagram */}
                <div className="flex flex-1 items-center justify-center overflow-hidden p-6">
                  <Suspense
                    fallback={
                      <div className="flex h-full w-full items-center justify-center text-gray-400">
                        Loading diagram…
                      </div>
                    }
                  >
                    {DiagramRenderer && <DiagramRenderer geometry={problem.geometry} />}
                  </Suspense>
                </div>

                {/* Answer panel */}
                <div className="w-52 flex-shrink-0 overflow-y-auto border-l border-gray-200 bg-white">
                  <AnswerPanel
                    schema={problem.answerSchema}
                    values={answers}
                    perField={lastCheck?.perField ?? null}
                    onChange={(key, val) => {
                      setAnswers((prev) => ({ ...prev, [key]: val }))
                      setLastCheck(null)
                      setIsDirty(true)
                    }}
                    readOnly={problemLocked}
                    correctAnswers={correctAnswers}
                  />
                </div>
              </div>

              <FeedbackPanel result={lastCheck} />
            </div>
          )}
        </div>

        {/* Action bar */}
        <ActionBar
          onPrev={() => { navigate_problem(currentIndex - 1) }}
          onNext={() => { navigate_problem(currentIndex + 1) }}
          onCheck={handleCheck}
          onSave={handleSave}
          onSubmit={handleSubmit}
          reviewMode={reviewMode}
          problemLocked={problemLocked}
          checking={checkMutation.isPending}
          saveStatus={saveStatus}
        />
      </div>
    </div>
  )
}
