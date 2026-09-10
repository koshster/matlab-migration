import { COLORS, GEOM } from './constants'
import { GroundBar, SupportFrame, TRIANGLE_POINTS } from './SupportGlyph'

interface RollerSupportProps {
  x: number
  y: number
  angleDeg: number
}

/**
 * Triangle, one wheel tangent to its base, then a ground bar below the wheel
 * (drawSupports.m:103-121). The roller's bar is shorter than the pin's.
 */
export default function RollerSupport({ x, y, angleDeg }: RollerSupportProps) {
  return (
    <SupportFrame x={x} y={y} angleDeg={angleDeg}>
      <polygon
        points={TRIANGLE_POINTS}
        fill={COLORS.rollerFill}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth * 0.7}
      />
      <circle
        cx={0}
        cy={GEOM.wheelCenterY}
        r={GEOM.wheelRadius}
        fill={COLORS.wheelFill}
        stroke={COLORS.outline}
        strokeWidth={GEOM.outlineWidth * 0.7}
      />
      <GroundBar y={GEOM.rollerBarY} halfLength={GEOM.rollerBarHalfLength} />
    </SupportFrame>
  )
}
