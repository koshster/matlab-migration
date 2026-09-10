import { COLORS, GEOM, OPACITY, WALL } from './constants'

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
 * Solid charcoal bar for a fixed-wall (cantilever) support. The bar is
 * perpendicular to the body at the anchor point, placed on the "outside"
 * (the side facing away from the body). The rotation convention here is the
 * same as for pins/rollers: 0 = face below, 90 = face right, etc.
 *
 * `wall` uses rotation + 180 from the generator (which points the wall code
 * along the body, not at the ground side), so `drawnRotation` in the rigid-body
 * Supports component does the flip before calling this.
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
