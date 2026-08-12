interface ForceArrowProps {
  node: { x: number; y: number }
  fx: number
  fy: number
  label: string
}

const ARROW_LEN = 1.8
const ARROW_ID_COUNTER = { n: 0 }

export default function ForceArrow({ node, fx, fy, label }: ForceArrowProps) {
  // Each arrow needs a unique marker id (multiple arrows in one SVG)
  const id = `arrowhead-${String(ARROW_ID_COUNTER.n++)}`

  const mag = Math.sqrt(fx * fx + fy * fy)
  if (mag === 0) return null

  // Unit vector in force direction
  const ux = fx / mag
  const uy = fy / mag

  // Arrow tip is at the node; tail is ARROW_LEN units away in the opposite direction
  const x1 = node.x - ux * ARROW_LEN
  const y1 = node.y - uy * ARROW_LEN
  const x2 = node.x
  const y2 = node.y

  // Label midpoint, offset perpendicular to arrow
  const lx = (x1 + x2) / 2 - uy * 0.45
  const ly = (y1 + y2) / 2 + ux * 0.45

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
        <text
          x={lx}
          y={ly}
          transform={`scale(1,-1) translate(0,${-2 * ly})`}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={0.42}
          fill="#dc2626"
          fontFamily="sans-serif"
          fontWeight="700"
        >
          {label}
        </text>
      )}
    </g>
  )
}
