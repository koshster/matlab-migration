import { Suspense, useState, useEffect } from 'react'
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

const TOTAL_PROBLEMS = 8

export default function WorkspaceLayout() {
  const { slug = '' } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const session = useSession()

  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number | null>>({})
  const [lastCheck, setLastCheck] = useState<CheckResult | null>(null)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const { data: assignment } = useAssignment(slug)
  const { data: problem, isLoading: problemLoading, isError: problemError } = useProblem(slug, currentIndex)
  const saveMutation = useSaveAnswers(slug, currentIndex)
  const checkMutation = useCheckAnswers(slug, currentIndex)
  const submitMutation = useSubmit(slug)

  const locked = assignment?.locked ?? false

  // Reset per-problem state when navigating
  useEffect(() => {
    setAnswers(problem?.savedAnswers ?? {})
    setLastCheck(null)
  }, [currentIndex, problem?.savedAnswers])

  function navigate_problem(index: number) {
    // Wrap: -1 → 7, 8 → 0
    const next = ((index % TOTAL_PROBLEMS) + TOTAL_PROBLEMS) % TOTAL_PROBLEMS
    setCurrentIndex(next)
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
            <div>
              <span className="text-sm font-semibold text-gray-800">
                {session.firstName} {session.lastName}
              </span>
              <span className="ml-2 text-xs text-gray-400">{session.studentId}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {saveStatus === 'saved' && (
              <span className="text-xs text-green-600">Saved ✓</span>
            )}
            {locked && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                Submitted
              </span>
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
                    }}
                    disabled={locked}
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
          locked={locked}
          checking={checkMutation.isPending}
          saveStatus={saveStatus}
        />
      </div>
    </div>
  )
}
