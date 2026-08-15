interface NodeProps {
  x: number
  y: number
}

export default function Node({ x, y }: NodeProps) {
  return <circle cx={x} cy={y} r={0.22} fill="#374151" stroke="#fff" strokeWidth={0.06} />
}
