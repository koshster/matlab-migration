import { COLORS, GEOM, TYPE } from '../shared/constants'
import FlipText from '../shared/FlipText'
import type { Placement } from './memberLabels'

interface MemberProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  /** Member number as shown in the diagram -- 1..n, not the S-subscript answer key. */
  number: number
  label: Placement
}

/**
 * A member is a "pipe": a filled, black-outlined quad running node-centre to
 * node-centre (plotTruss.m:31-40). The round joint caps are drawn by `Node`,
 * which paints after every member.
 */
export default function Member({ from, to, number, label }: MemberProps) {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1

  // Perpendicular is 90 degrees CCW of from->to, exactly as plotTruss.m:57.
  const px = -dy / len
  const py = dx / len
  const r = GEOM.memberHalfWidth

  const corners: Array<[number, number]> = [
    [from.x - r * px, from.y - r * py],
    [from.x + r * px, from.y + r * py],
    [to.x + r * px, to.y + r * py],
    [to.x - r * px, to.y - r * py],
  ]

  return (
    <g>
      <polygon
        points={corners.map(([x, y]) => `${String(x)},${String(y)}`).join(' ')}
        fill={COLORS.member}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth}
      />
      <FlipText
        x={label.x}
        y={label.y}
        fontSize={TYPE.memberLabel}
        fill={COLORS.memberLabel}
        anchor={label.anchor}
        weight="bold"
      >
        {number}
      </FlipText>
    </g>
  )
}
