interface RollerSupportProps {
  x: number
  y: number
  angleDeg: number
}

const TRIANGLE = '0,0 -0.45,-0.65 0.45,-0.65'

export default function RollerSupport({ x, y, angleDeg }: RollerSupportProps) {
  return (
    <g transform={`translate(${x},${y}) rotate(${-angleDeg})`}>
      <polygon points={TRIANGLE} fill="#d1d5db" stroke="#6b7280" strokeWidth={0.05} />
      {/* Roller wheel circle at triangle centroid (0, -0.65*2/3) */}
      <circle cx={0} cy={-0.43} r={0.16} fill="#fff" stroke="#6b7280" strokeWidth={0.05} />
      {/* Ground line */}
      <line x1={-0.55} y1={-0.72} x2={0.55} y2={-0.72} stroke="#6b7280" strokeWidth={0.07} />
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
