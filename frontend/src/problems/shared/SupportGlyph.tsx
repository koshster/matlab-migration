import { COLORS, GEOM, OPACITY, TYPE, WALL } from './constants'
import MathLabel from './MathLabel'
import type { Segment } from './forceShift'
import { placeSupportLabel } from './supportLabels'

/** drawSupports.m:83-88 — equilateral triangle, side 0.3, apex tucked under the joint. */
export const TRIANGLE_POINTS = [
  `0,${String(GEOM.triangleApexY)}`,
  `${String(-GEOM.triangleHalfBase)},${String(GEOM.triangleBaseY)}`,
  `${String(GEOM.triangleHalfBase)},${String(GEOM.triangleBaseY)}`,
].join(' ')

/**
 * The flat ground bar under a pin or roller (drawSupports.m:110-133). A plain
 * filled bar — the MATLAB renderer draws no hatch ticks.
 */
export function GroundBar({ y, halfLength }: { y: number; halfLength: number }) {
  return (
    <rect
      x={-halfLength}
      y={y - GEOM.barThickness}
      width={halfLength * 2}
      height={GEOM.barThickness}
      fill={COLORS.ground}
    />
  )
}

/**
 * Wraps a support glyph at its node. `angleDeg` rotates the whole assembly CCW
 * about the node (drawSupports.m:88): 0 puts the base below the node, 90 to the
 * right, 180 above, 270 to the left. Child coordinates are already physics
 * coordinates (the flip happens on the group above), so a plain positive
 * `rotate` is CCW here.
 *
 * The group is drawn slightly transparent so a member passing under the
 * triangle stays visible; opacity is set on the group, not the shapes, so the
 * triangle, wheel and bar do not bleed through each other.
 */
export function SupportFrame({
  x,
  y,
  angleDeg,
  children,
}: {
  x: number
  y: number
  angleDeg: number
  children: React.ReactNode
}) {
  return (
    <g
      transform={`translate(${String(x)},${String(y)}) rotate(${String(angleDeg)})`}
      opacity={OPACITY.support}
    >
      {children}
    </g>
  )
}

/**
 * The letter that ties a support in the picture to the `reaction_Ax` style
 * answer fields. It sits just clear of the node on the side *opposite* the
 * support base, so it never lands inside the glyph or under the ground bar
 * (ppt/media/image4.png: `A`'s support faces right, its letter sits left).
 *
 * `angleDeg` is the drawn base angle, i.e. the same value handed to
 * `SupportFrame` — callers that have to flip a wall must flip before calling.
 */
export function SupportLabel({
  x,
  y,
  angleDeg,
  label,
  segments = [],
}: {
  x: number
  y: number
  angleDeg: number
  label: string
  /** Body segments to keep the letter off; see `placeSupportLabel`. */
  segments?: Segment[]
}) {
  if (label === '') return null
  const at = placeSupportLabel({ x, y }, angleDeg, segments)
  return (
    <MathLabel
      x={at.x}
      y={at.y}
      label={label}
      fontSize={TYPE.supportLabel}
      fill={COLORS.outline}
      anchor="middle"
    />
  )
}

/**
 * Solid charcoal bar for a fixed-wall (cantilever) support, drawn across the
 * body's end so the member appears to run into it.
 *
 * `angleDeg` is a base angle on the same convention as `baseDir` and
 * `SupportFrame` — 0 = bar below the node, 90 = bar to its right. The
 * generator's own wall rotation is not on that convention; `wallBaseAngle` in
 * WallSupport converts it.
 */
export function WallBar({
  x,
  y,
  angleDeg,
}: {
  x: number
  y: number
  angleDeg: number
}) {
  return (
    <g
      transform={`translate(${String(x)},${String(y)}) rotate(${String(angleDeg)})`}
      opacity={OPACITY.support}
    >
      <rect
        x={-WALL.barHalfLength}
        y={-WALL.barThickness / 2}
        width={WALL.barHalfLength * 2}
        height={WALL.barThickness}
        fill={WALL.barColor}
      />
    </g>
  )
}
