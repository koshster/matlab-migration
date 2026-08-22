interface MemberProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  label: string
  fontSize: number
  offset: number
  centroid: { x: number; y: number }
}

export default function Member({ from, to, label, fontSize, offset, centroid }: MemberProps) {
  const mx = (from.x + to.x) / 2
  const my = (from.y + to.y) / 2

  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.sqrt(dx * dx + dy * dy) || 1

  // Two perpendicular unit vectors
  const p1x = -dy / len, p1y = dx / len
  const p2x = dy / len, p2y = -dx / len

  // Pick the one pointing AWAY from the truss centroid so labels radiate outward
  const dot1 = p1x * (centroid.x - mx) + p1y * (centroid.y - my)
  const perpX = dot1 <= 0 ? p1x : p2x
  const perpY = dot1 <= 0 ? p1y : p2y

  const lx = mx + perpX * offset
  const ly = my + perpY * offset

  const bgW = label.length * fontSize * 0.65
  const bgH = fontSize * 1.5

  return (
    <g>
      <line
        x1={from.x} y1={from.y}
        x2={to.x} y2={to.y}
        stroke="#6b7280"
        strokeWidth={0.18}
        strokeLinecap="round"
      />
      {/* Rect and text share one counter-flip group so they occupy the same coordinate space */}
      <g transform={`scale(1,-1) translate(0,${-2 * ly})`}>
        <rect
          x={lx - bgW / 2}
          y={ly - bgH / 2}
          width={bgW}
          height={bgH}
          rx={bgH / 4}
          fill="white"
          fillOpacity={0.85}
        />
        <text
          x={lx}
          y={ly}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSize}
          fill="#2563eb"
          fontFamily="sans-serif"
          fontWeight="600"
        >
          {label}
        </text>
      </g>
    </g>
  )
}
