import { useId } from 'react'
import FlipText from './FlipText'

interface MomentArcProps {
  x: number
  y: number
  /** +1 counter-clockwise, -1 clockwise. */
  direction: number
  /** Bisector of the arc, pointing at the free side of the joint (degrees). */
  arrowAngle: number
  /** Angular sweep of the arc (degrees); the rest is the gap. */
  arcAngle: number
  label: string
  fontSize: number
}

const RADIUS = 0.62
// Markers scale with stroke width, so a 6-unit marker on a 0.09 stroke draws a
// 0.54-unit arrowhead -- bigger than the arc it caps. Keep it well under RADIUS.
const MARKER = 3.5
const STROKE = 0.09
const COLOR = '#7c3aed'

const toRad = (deg: number): number => (deg * Math.PI) / 180

/**
 * Concentrated couple: an arc with an arrowhead on one end.
 *
 * The generator picks `arrowAngle` to point at whichever side of the joint has
 * no body attached, and `arcAngle` for how far round to sweep, so the arc is
 * centred on the bisector and the gap lands over the members. The arrowhead
 * goes on the end the rotation runs toward -- leading end for counter-
 * clockwise, trailing end for clockwise -- which is what shows the sign.
 */
export default function MomentArc({
  x,
  y,
  direction,
  arrowAngle,
  arcAngle,
  label,
  fontSize,
}: MomentArcProps) {
  const markerId = `rb-moment-${useId()}`

  const sweep = Math.min(Math.max(arcAngle, 10), 350)
  const start = arrowAngle - sweep / 2
  const end = arrowAngle + sweep / 2

  const startX = x + RADIUS * Math.cos(toRad(start))
  const startY = y + RADIUS * Math.sin(toRad(start))
  const endX = x + RADIUS * Math.cos(toRad(end))
  const endY = y + RADIUS * Math.sin(toRad(end))

  const largeArc = sweep > 180 ? 1 : 0
  const ccw = direction >= 0

  // Draw in the direction the couple turns, so `markerEnd` lands the arrowhead
  // on the correct end without a second path. `sweepFlag` is 1 for increasing
  // angle, which is counter-clockwise in the diagram's y-up frame.
  const d = ccw
    ? `M ${String(startX)} ${String(startY)} A ${String(RADIUS)} ${String(RADIUS)} 0 ${String(largeArc)} 1 ${String(endX)} ${String(endY)}`
    : `M ${String(endX)} ${String(endY)} A ${String(RADIUS)} ${String(RADIUS)} 0 ${String(largeArc)} 0 ${String(startX)} ${String(startY)}`

  const labelDistance = RADIUS + fontSize * 1.4
  const labelX = x + labelDistance * Math.cos(toRad(arrowAngle))
  const labelY = y + labelDistance * Math.sin(toRad(arrowAngle))

  return (
    <g>
      <defs>
        <marker
          id={markerId}
          markerWidth={MARKER}
          markerHeight={MARKER}
          refX={MARKER}
          refY={MARKER / 2}
          orient="auto"
        >
          <path d={`M0,0 L0,${String(MARKER)} L${String(MARKER)},${String(MARKER / 2)} z`} fill={COLOR} />
        </marker>
      </defs>
      <path
        d={d}
        fill="none"
        stroke={COLOR}
        strokeWidth={STROKE}
        markerEnd={`url(#${markerId})`}
      />
      {label && (
        <FlipText x={labelX} y={labelY} fontSize={fontSize} fill={COLOR} plate>
          {label}
        </FlipText>
      )}
    </g>
  )
}
