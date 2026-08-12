interface PinSupportProps {
  x: number
  y: number
  angleDeg: number
}

// Triangle with apex at (0,0) pointing down in physics coords (y-up).
// After the parent scale(1,-1) flip, "down in physics" = down on screen = correct support symbol.
const TRIANGLE = '0,0 -0.45,-0.65 0.45,-0.65'

// Hatching line below triangle base
const HATCH = '-0.55,-0.72 0.55,-0.72'

export default function PinSupport({ x, y, angleDeg }: PinSupportProps) {
  return (
    <g transform={`translate(${x},${y}) rotate(${-angleDeg})`}>
      <polygon points={TRIANGLE} fill="#9ca3af" stroke="#6b7280" strokeWidth={0.05} />
      <line
        x1={-0.55} y1={-0.72} x2={0.55} y2={-0.72}
        stroke="#6b7280" strokeWidth={0.07}
      />
      {/* Hatching ticks */}
      {[-0.4, -0.2, 0, 0.2, 0.4].map((dx) => (
        <line
          key={dx}
          x1={dx} y1={-0.72} x2={dx - 0.12} y2={-0.92}
          stroke="#6b7280" strokeWidth={0.05}
        />
      ))}
    </g>
  )
}

export { HATCH }
