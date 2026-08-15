import type { components } from '@statics/contract/src/index'

type Prompt = components['schemas']['Prompt']

export default function InstructionPanel({ prompt }: { prompt: Prompt }) {
  return (
    <div className="border-b border-gray-200 bg-white px-6 py-4">
      <h2 className="text-base font-semibold text-gray-900">{prompt.title}</h2>
      <p className="mt-1 text-sm text-gray-600">{prompt.body}</p>
      {prompt.notes.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {prompt.notes.map((note, i) => (
            <li key={i} className="text-xs text-gray-500">
              • {note}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
