import { arrowPolygon, COLORS, GEOM } from '../shared/constants'
import FlipText from '../shared/FlipText'
import { splitLabel } from '../shared/labels'

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
}

const RADIUS = 0.62
const STROKE = 0.09
const ARROW_LEN = GEOM.arrowLength * 0.5

const toRad = (deg: number): number => (deg * Math.PI) / 180

/**
 * Concentrated couple: an arc with an arrowhead on one end.
 *
 * The generator picks `arrowAngle` to point at whichever side of the joint has
 * no body attached, and `arcAngle` for how far round to sweep, so the arc is
 * centred on the bisector and the gap lands over the members. The arrowhead
 * goes on the leading end of the rotation direction, which shows the sign.
 */
export default function MomentArc({
  x,
  y,
  direction,
  arrowAngle,
  arcAngle,
  label,
}: MomentArcProps) {
  const sweep = Math.min(Math.max(arcAngle, 10), 350)
  const start = arrowAngle - sweep / 2
  const end = arrowAngle + sweep / 2
  const ccw = direction >= 0

  const startRad = toRad(start)
  const endRad = toRad(end)

  const startX = x + RADIUS * Math.cos(startRad)
  const startY = y + RADIUS * Math.sin(startRad)
  const endX = x + RADIUS * Math.cos(endRad)
  const endY = y + RADIUS * Math.sin(endRad)

  const largeArc = sweep > 180 ? 1 : 0

  // Draw arc from start → end (CCW) or end → start (CW).
  const d = ccw
    ? `M ${String(startX)} ${String(startY)} A ${String(RADIUS)} ${String(RADIUS)} 0 ${String(largeArc)} 1 ${String(endX)} ${String(endY)}`
    : `M ${String(endX)} ${String(endY)} A ${String(RADIUS)} ${String(RADIUS)} 0 ${String(largeArc)} 0 ${String(startX)} ${String(startY)}`

  // Tangent direction at the tip of the arc (where the arrowhead goes).
  // For CCW: tip is at `end`; tangent = (-sin(end), cos(end)).
  // For CW: tip is at `start` (path end when reversed); tangent = (sin(start), -cos(start)).
  const tipAngleRad = ccw ? endRad : startRad
  const tipX = x + RADIUS * Math.cos(tipAngleRad)
  const tipY = y + RADIUS * Math.sin(tipAngleRad)
  const tanX = ccw ? -Math.sin(tipAngleRad) : Math.sin(tipAngleRad)
  const tanY = ccw ? Math.cos(tipAngleRad) : -Math.cos(tipAngleRad)

  // Arrow polygon: tail back from the tip, pointing in the tangent direction.
  const tailX = tipX - tanX * ARROW_LEN
  const tailY = tipY - tanY * ARROW_LEN
  const arrowPts = arrowPolygon(ARROW_LEN)
    .map(([along, across]) => {
      const wx = tailX + along * tanX + across * -tanY
      const wy = tailY + along * tanY + across * tanX
      return `${String(wx)},${String(wy)}`
    })
    .join(' ')

  const labelDistance = RADIUS + GEOM.arrowLength * 1.1
  const labelX = x + labelDistance * Math.cos(toRad(arrowAngle))
  const labelY = y + labelDistance * Math.sin(toRad(arrowAngle))

  const { head, unit } = splitLabel(label)

  return (
    <g>
      <path d={d} fill="none" stroke={COLORS.force} strokeWidth={STROKE} />
      <polygon points={arrowPts} fill={COLORS.force} />
      {label !== '' && (
        <FlipText
          x={labelX}
          y={labelY}
          fontSize={0.2}
          fill={COLORS.force}
          anchor="middle"
        >
          {head}
          {unit ? <tspan fontStyle="italic">F</tspan> : null}
        </FlipText>
      )}
    </g>
  )
}
