import { COLORS, GEOM } from '../shared/constants'

interface NodeProps {
  x: number
  y: number
}

/**
 * The joint glyph is two overlaid markers (plotTruss.m:43-44, :74): the pipe's
 * round end cap, which closes the member outlines, plus a small grey dot.
 */
export default function Node({ x, y }: NodeProps) {
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        r={GEOM.nodeCapRadius}
        fill={COLORS.member}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth}
      />
      <circle
        cx={x}
        cy={y}
        r={GEOM.nodeDotRadius}
        fill={COLORS.nodeDot}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth * 0.6}
      />
    </g>
  )
}
