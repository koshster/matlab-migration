import { arrowPolygon, COLORS, GEOM, OPACITY, TYPE } from './constants'
import FlipText from './FlipText'
import { splitLabel } from './labels'

interface ForceArrowProps {
  node: { x: number; y: number }
  fx: number
  fy: number
  label: string
  /**
   * True when the force direction is blocked by structure, so the arrow slides
   * back one full length and its tip lands on the node instead of its tail
   * (drawForces.m:58-103).
   */
  shifted: boolean
}

export default function ForceArrow({ node, fx, fy, label, shifted }: ForceArrowProps) {
  const mag = Math.hypot(fx, fy)
  if (mag === 0) return null

  const ux = fx / mag
  const uy = fy / mag
  const len = GEOM.arrowLength

  // Tail at the node by default; shifted back by one arrow length when blocked.
  const tailX = shifted ? node.x - ux * len : node.x
  const tailY = shifted ? node.y - uy * len : node.y

  // Arrow-local (along, across) -> world, so no rotate transform is needed.
  const points = arrowPolygon(len)
    .map(([along, across]) => {
      const wx = tailX + along * ux + across * -uy
      const wy = tailY + along * uy + across * ux
      return `${String(wx)},${String(wy)}`
    })
    .join(' ')

  const factor = shifted ? GEOM.forceLabelShifted : GEOM.forceLabelUnshifted
  const lx = node.x + factor * len * ux
  const ly = node.y + factor * len * uy

  // drawForces.m:16-22 — the text grows away from the arrow, not back over it.
  const horizontal = Math.abs(ux) > Math.abs(uy)
  const anchor = horizontal ? (ux < 0 !== shifted ? 'end' : 'start') : 'middle'

  const { head, unit } = splitLabel(label)

  return (
    <g>
      {/* Slightly transparent so a member under the shaft still reads; the
          label stays fully opaque because it has to be read exactly. */}
      <polygon points={points} fill={COLORS.force} opacity={OPACITY.force} />
      {label !== '' && (
        <FlipText x={lx} y={ly} fontSize={TYPE.forceLabel} fill={COLORS.force} anchor={anchor}>
          {head}
          {unit ? <tspan fontStyle="italic">F</tspan> : null}
        </FlipText>
      )}
    </g>
  )
}
