import { Routes, Route } from 'react-router-dom'

function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50">
      <h1 className="text-4xl font-bold text-gray-900">Statics Platform</h1>
      <p className="text-lg text-gray-500">Phase 0 scaffold — backend and frontend wiring up.</p>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  )
}
