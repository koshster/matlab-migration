export default function FallbackDiagram({ geometry }: { geometry: unknown }) {
  return (
    <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500">
      <div>
        <p className="font-medium">Unknown problem type</p>
        <pre className="mt-2 max-h-48 overflow-auto text-left text-xs">
          {JSON.stringify(geometry, null, 2)}
        </pre>
      </div>
    </div>
  )
}
