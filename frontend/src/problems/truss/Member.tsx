interface MemberProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  label: string
}

export default function Member({ from, to, label }: MemberProps) {
  const mx = (from.x + to.x) / 2
  const my = (from.y + to.y) / 2

  return (
    <g>
      <line
        x1={from.x} y1={from.y}
        x2={to.x}   y2={to.y}
        stroke="#6b7280"
        strokeWidth={0.18}
        strokeLinecap="round"
      />
      {/* Counter-flip text so it reads right-side up after parent scale(1,-1) */}
      <text
        x={mx}
        y={my}
        transform={`scale(1,-1) translate(0,${-2 * my})`}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={0.45}
        fill="#2563eb"
        fontFamily="sans-serif"
        fontWeight="600"
      >
        {label}
      </text>
    </g>
  )
}
