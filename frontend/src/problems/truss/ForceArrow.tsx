interface ForceArrowProps {
  node: { x: number; y: number }
  fx: number
  fy: number
  label: string
  fontSize: number
}

const ARROW_LEN = 1.8
const ARROW_ID_COUNTER = { n: 0 }

export default function ForceArrow({ node, fx, fy, label, fontSize }: ForceArrowProps) {
  const id = `arrowhead-${String(ARROW_ID_COUNTER.n++)}`

  const mag = Math.sqrt(fx * fx + fy * fy)
  if (mag === 0) return null

  const ux = fx / mag
  const uy = fy / mag

  // Tip at node; tail is ARROW_LEN units back
  const x1 = node.x - ux * ARROW_LEN
  const y1 = node.y - uy * ARROW_LEN
  const x2 = node.x
  const y2 = node.y

  // Place label 3/4 of the way from tip toward tail — keeps it away from the node cluster
  const tlx = x2 + (x1 - x2) * 0.75
  const tly = y2 + (y1 - y2) * 0.75
  const labelOffset = fontSize * 1.2
  const lx = tlx - uy * labelOffset
  const ly = tly + ux * labelOffset

  const bgW = label.length * fontSize * 0.65
  const bgH = fontSize * 1.5

  return (
    <g>
      <defs>
        <marker
          id={id}
          markerWidth={6}
          markerHeight={6}
          refX={5}
          refY={3}
          orient="auto"
        >
          <path d="M0,0 L0,6 L6,3 z" fill="#dc2626" />
        </marker>
      </defs>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke="#dc2626"
        strokeWidth={0.1}
        markerEnd={`url(#${id})`}
      />
      {label && (
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
            fill="#dc2626"
            fontFamily="sans-serif"
            fontWeight="700"
          >
            {label}
          </text>
        </g>
      )}
    </g>
  )
}
