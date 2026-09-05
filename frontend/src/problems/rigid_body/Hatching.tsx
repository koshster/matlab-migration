interface HatchingProps {
  /** Half-width of the ground line, in diagram units. */
  halfWidth: number
  /** Where the ground line sits relative to the anchor (physics coords, y-up). */
  y: number
}

/**
 * Ground line plus the diagonal ticks that mark "fixed to the world".
 *
 * Drawn in physics coords (y-up) like everything else inside the diagram's
 * flip group, so `y` is negative when the ground sits below the anchor.
 */
export default function Hatching({ halfWidth, y }: HatchingProps) {
  const step = (halfWidth * 2) / 5
  const ticks = Array.from({ length: 6 }, (_, i) => -halfWidth + i * step)

  return (
    <g>
      <line x1={-halfWidth} y1={y} x2={halfWidth} y2={y} stroke="#6b7280" strokeWidth={0.07} />
      {ticks.map((dx) => (
        <line
          key={dx}
          x1={dx}
          y1={y}
          x2={dx - 0.12}
          y2={y - 0.2}
          stroke="#6b7280"
          strokeWidth={0.05}
        />
      ))}
    </g>
  )
}
