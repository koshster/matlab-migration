import { COLORS, GEOM } from './constants'
import { GroundBar, SupportFrame, TRIANGLE_POINTS } from './SupportGlyph'

interface PinSupportProps {
  x: number
  y: number
  angleDeg: number
}

/** Triangle plus a ground bar flush with its base (drawSupports.m:120-127). */
export default function PinSupport({ x, y, angleDeg }: PinSupportProps) {
  return (
    <SupportFrame x={x} y={y} angleDeg={angleDeg}>
      <polygon
        points={TRIANGLE_POINTS}
        fill={COLORS.pinFill}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth * 0.7}
      />
      <GroundBar y={GEOM.pinBarY} halfLength={GEOM.pinBarHalfLength} />
    </SupportFrame>
  )
}
