import { COLORS, MOMENT, OPACITY, TYPE } from '../shared/constants'
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
  const { radius: r, headLength, headHalfWidth } = MOMENT
  const sweep = Math.min(Math.max(arcAngle, MOMENT.minSweepDeg), MOMENT.maxSweepDeg)
  const ccw = direction >= 0
  const turn = ccw ? 1 : -1

  const on = (rad: number): [number, number] => [x + r * Math.cos(rad), y + r * Math.sin(rad)]

  // The arc runs from its trailing end round to the tip, so `turn` alone fixes
  // which physical end the arrowhead lands on.
  const tailRad = toRad(arrowAngle - turn * (sweep / 2))
  const tipRad = toRad(arrowAngle + turn * (sweep / 2))
  const [tipX, tipY] = on(tipRad)

  // Head length as an angle, so tip and base both sit on the arc's circle and
  // the triangle hugs the curve instead of flying off along the tangent. It can
  // never eat more than half the sweep, however tight the generator's gap.
  const headArcRad = Math.min(headLength / r, toRad(sweep) / 2)
  const baseRad = tipRad - turn * headArcRad

  // Stop the stroke a third of the way inside the head rather than at the tip:
  // a round cap at the point would blunt it, but ending flush at the base would
  // leave a hairline gap. The overlap hides under the solid fill.
  const strokeEndRad = tipRad - turn * headArcRad * (2 / 3)
  const [fromX, fromY] = on(tailRad)
  const [toX, toY] = on(strokeEndRad)

  const drawnSweep = sweep - (headArcRad * (2 / 3) * 180) / Math.PI
  const largeArc = drawnSweep > 180 ? 1 : 0
  const arcFlag = ccw ? 1 : 0
  const d = `M ${String(fromX)} ${String(fromY)} A ${String(r)} ${String(r)} 0 ${String(largeArc)} ${String(arcFlag)} ${String(toX)} ${String(toY)}`

  // Solid triangle: tip on the arc, base straddling it radially one head-length
  // back round the curve.
  const [baseX, baseY] = on(baseRad)
  const outX = Math.cos(baseRad)
  const outY = Math.sin(baseRad)
  const arrowPts = [
    [tipX, tipY],
    [baseX + outX * headHalfWidth, baseY + outY * headHalfWidth],
    [baseX - outX * headHalfWidth, baseY - outY * headHalfWidth],
  ]
    .map(([px, py]) => `${String(px)},${String(py)}`)
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
