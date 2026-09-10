import { arrowPolygon, COLORS, MOMENT, OPACITY, TYPE } from '../shared/constants'
import MathLabel from '../shared/MathLabel'

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

const toRad = (deg: number): number => (deg * Math.PI) / 180

/**
 * Concentrated couple: an arc with an arrowhead on one end.
 *
 * The generator picks `arrowAngle` to point at whichever side of the joint has
 * no body attached, and `arcAngle` for how far round to sweep, so the arc is
 * centred on the bisector and the gap lands over the body. The arrowhead goes
 * on the leading end of the rotation direction, which shows the sign.
 */
export default function MomentArc({
  x,
  y,
  direction,
  arrowAngle,
  arcAngle,
  label,
}: MomentArcProps) {
  const { radius: r, arrowLength: headLen } = MOMENT
  const sweep = Math.min(Math.max(arcAngle, MOMENT.minSweepDeg), MOMENT.maxSweepDeg)
  const startRad = toRad(arrowAngle - sweep / 2)
  const endRad = toRad(arrowAngle + sweep / 2)
  const ccw = direction >= 0

  const on = (rad: number): [number, number] => [x + r * Math.cos(rad), y + r * Math.sin(rad)]
  const [startX, startY] = on(startRad)
  const [endX, endY] = on(endRad)

  const largeArc = sweep > 180 ? 1 : 0

  // Draw start -> end for CCW, end -> start for CW, so the path always ends
  // where the arrowhead goes.
  const [fromX, fromY, toX, toY, arcFlag] = ccw
    ? [startX, startY, endX, endY, 1]
    : [endX, endY, startX, startY, 0]
  const d = `M ${String(fromX)} ${String(fromY)} A ${String(r)} ${String(r)} 0 ${String(largeArc)} ${String(arcFlag)} ${String(toX)} ${String(toY)}`

  // Tangent at the tip, in the direction of travel: the radial unit vector
  // turned a quarter turn the way the arc sweeps.
  const tipRad = ccw ? endRad : startRad
  const turn = ccw ? 1 : -1
  const tanX = -turn * Math.sin(tipRad)
  const tanY = turn * Math.cos(tipRad)

  const tailX = toX - tanX * headLen
  const tailY = toY - tanY * headLen
  const arrowPts = arrowPolygon(headLen)
    .map(([along, across]) => {
      const wx = tailX + along * tanX + across * -tanY
      const wy = tailY + along * tanY + across * tanX
      return `${String(wx)},${String(wy)}`
    })
    .join(' ')

  const labelDistance = r + MOMENT.labelGap
  const labelX = x + labelDistance * Math.cos(toRad(arrowAngle))
  const labelY = y + labelDistance * Math.sin(toRad(arrowAngle))

  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={COLORS.force}
        strokeWidth={MOMENT.strokeWidth}
        strokeLinecap="round"
        opacity={OPACITY.force}
      />
      <polygon points={arrowPts} fill={COLORS.force} opacity={OPACITY.force} />
      {label !== '' && (
        <MathLabel
          x={labelX}
          y={labelY}
          label={label}
          fontSize={TYPE.forceLabel}
          fill={COLORS.force}
          anchor="middle"
        />
      )}
    </g>
  )
}
