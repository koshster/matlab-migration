import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStudentLogin, useStudentRegister } from '../api/hooks'
import { useSetSession } from '../context/SessionContext'
import { ApiError } from '../api/client'

type Tab = 'login' | 'register'

export default function StudentAuthPage() {
  const navigate = useNavigate()
  const setSession = useSetSession()
  const [tab, setTab] = useState<Tab>('login')
  const [registeredPid, setRegisteredPid] = useState<string | null>(null)

  const loginMutation = useStudentLogin()
  const registerMutation = useStudentRegister()

  const [loginFields, setLoginFields] = useState({ pid: '', password: '' })
  const [registerFields, setRegisterFields] = useState({
    pid: '',
    firstName: '',
    lastName: '',
    password: '',
    confirmPassword: '',
  })
  const [passwordMismatch, setPasswordMismatch] = useState(false)

  function handleLoginChange(e: React.ChangeEvent<HTMLInputElement>) {
    setLoginFields((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  function handleRegisterChange(e: React.ChangeEvent<HTMLInputElement>) {
    setRegisterFields((f) => ({ ...f, [e.target.name]: e.target.value }))
    if (e.target.name === 'confirmPassword' || e.target.name === 'password') {
      setPasswordMismatch(false)
    }
  }

  function handleLogin(e: FormEvent) {
    e.preventDefault()
    loginMutation.mutate(loginFields, {
      onSuccess: (data) => {
        setSession({ studentId: data.student.id, firstName: data.student.firstName, lastName: data.student.lastName })
        navigate('/student/dashboard')
      },
    })
  }

  function handleRegister(e: FormEvent) {
    e.preventDefault()
    if (registerFields.password !== registerFields.confirmPassword) {
      setPasswordMismatch(true)
      return
    }
    // Built explicitly so confirmPassword — or any field added to the form
    // later — can never be sent to the API by accident.
    const body = {
      pid: registerFields.pid,
      firstName: registerFields.firstName,
      lastName: registerFields.lastName,
      password: registerFields.password,
    }
    registerMutation.mutate(body, {
      onSuccess: () => {
        setRegisteredPid(body.pid)
        setRegisterFields({ pid: '', firstName: '', lastName: '', password: '', confirmPassword: '' })
        setTab('login')
      },
    })
  }

  const loginError = loginMutation.error
  const registerError = registerMutation.error

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-md">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Statics Platform</h1>
        <p className="mb-6 text-sm text-gray-500">Student portal</p>

        {/* Tabs */}
        <div className="mb-6 flex rounded-lg border border-gray-200 p-1">
          {(['login', 'register'] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => { setTab(t); setRegisteredPid(null) }}
              className={[
                'flex-1 rounded-md py-1.5 text-sm font-medium transition-colors',
                tab === t
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700',
              ].join(' ')}
            >
              {t === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        {tab === 'login' && registeredPid && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            Account created for <strong>{registeredPid}</strong>. Sign in to continue.
          </div>
        )}

        {tab === 'login' ? (
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <Field
              id="login-pid"
              name="pid"
              label="Student ID (PID)"
              type="text"
              value={loginFields.pid}
              onChange={handleLoginChange}
              disabled={loginMutation.isPending}
              placeholder="A12345678"
            />
            <Field
              id="login-password"
              name="password"
              label="Password"
              type="password"
              value={loginFields.password}
              onChange={handleLoginChange}
              disabled={loginMutation.isPending}
              placeholder="••••••••"
            />

            {loginError && (
              <p className="text-sm text-red-600">
                {loginError instanceof ApiError && loginError.status === 401
                  ? 'Incorrect PID or password.'
                  : 'Something went wrong. Please try again.'}
              </p>
            )}

            <button
              type="submit"
              disabled={loginMutation.isPending || !loginFields.pid || !loginFields.password}
              className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loginMutation.isPending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="flex flex-col gap-4">
            <Field
              id="reg-pid"
              name="pid"
              label="Student ID (PID)"
              type="text"
              value={registerFields.pid}
              onChange={handleRegisterChange}
              disabled={registerMutation.isPending}
              placeholder="A12345678"
            />
            <div className="flex gap-3">
              <Field
                id="reg-first"
                name="firstName"
                label="First Name"
                type="text"
                value={registerFields.firstName}
                onChange={handleRegisterChange}
                disabled={registerMutation.isPending}
                placeholder="John"
              />
              <Field
                id="reg-last"
                name="lastName"
                label="Last Name"
                type="text"
                value={registerFields.lastName}
                onChange={handleRegisterChange}
                disabled={registerMutation.isPending}
                placeholder="Doe"
              />
            </div>
            <Field
              id="reg-password"
              name="password"
              label="Password"
              type="password"
              value={registerFields.password}
              onChange={handleRegisterChange}
              disabled={registerMutation.isPending}
              placeholder="••••••••"
            />
            <Field
              id="reg-confirm"
              name="confirmPassword"
              label="Confirm Password"
              type="password"
              value={registerFields.confirmPassword}
              onChange={handleRegisterChange}
              disabled={registerMutation.isPending}
              placeholder="••••••••"
              error={passwordMismatch ? 'Passwords do not match.' : undefined}
            />

            {registerError && (
              <p className="text-sm text-red-600">
                {registerError instanceof ApiError && registerError.status === 409
                  ? 'An account with that PID already exists.'
                  : 'Something went wrong. Please try again.'}
              </p>
            )}

            <button
              type="submit"
              disabled={
                registerMutation.isPending ||
                !registerFields.pid ||
                !registerFields.firstName ||
                !registerFields.lastName ||
                !registerFields.password ||
                !registerFields.confirmPassword
              }
              className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {registerMutation.isPending ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        )}
      </div>
    </main>
  )
}

interface FieldProps {
  id: string
  name: string
  label: string
  type: 'text' | 'email' | 'password'
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  disabled: boolean
  placeholder: string
  error?: string
}

function Field({ id, name, label, type, value, onChange, disabled, placeholder, error }: FieldProps) {
  return (
    <div className="flex-1">
      <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        disabled={disabled}
        placeholder={placeholder}
        autoComplete={type === 'password' ? 'current-password' : type === 'email' ? 'email' : 'off'}
        className={[
          'w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1 disabled:opacity-50',
          error
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500',
        ].join(' ')}
        required
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
