import { GEOM, TYPE } from './constants'
import { baseDir } from './supportGeometry'
import type { Segment } from './forceShift'

export interface Point {
  x: number
  y: number
}

/**
 * Where to set a support's letter.
 *
 * Offsetting straight out from the support base is not enough on its own: the
 * base points at the *free* side, so its opposite is the side the body is on,
 * and on an elbow or a mid-span support the letter lands on a bar
 * (ppt/media/image34.png has `A` on an elbow and the deck puts it diagonally
 * out from the corner, not straight through the member).
 *
 * So: try the eight compass directions, skip the ones that point into the
 * support glyph, and take the most-preferred one whose letter clears every bar.
 * Preference is "as close to directly opposite the base as possible", which
 * reduces to the simple straight-out offset whenever that side happens to be
 * clear — which is the common case and what the deck shows for `B` and `C` in
 * image34 and for both letters in image6.
 */

/** Compass directions, in a fixed order so ties resolve deterministically. */
const COMPASS: Point[] = (() => {
  const r = Math.SQRT1_2
  return [
    { x: 1, y: 0 },
    { x: r, y: r },
    { x: 0, y: 1 },
    { x: -r, y: r },
    { x: -1, y: 0 },
    { x: -r, y: -r },
    { x: 0, y: -1 },
    { x: r, y: -r },
  ]
})()

/**
 * Rings to try, nearest first. The second ring is the escape hatch for a
 * support tucked into a corner where nothing clears at the normal distance.
 */
const RINGS = [1, 1.7] as const

/** cos(35 deg): closer than this to the base direction and the glyph is in the way. */
const GLYPH_CONE = 0.82

/** Half the letter's footprint, so "clear" means clear of the glyph box, not its centre. */
const LETTER_RADIUS = TYPE.supportLabel * 0.6

function distanceToSegment(p: Point, { from, to }: Segment): number {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const lenSq = dx * dx + dy * dy
  if (lenSq < 1e-18) return Math.hypot(p.x - from.x, p.y - from.y)
  const t = Math.min(Math.max(((p.x - from.x) * dx + (p.y - from.y) * dy) / lenSq, 0), 1)
  return Math.hypot(p.x - (from.x + t * dx), p.y - (from.y + t * dy))
}

export function placeSupportLabel(at: Point, baseAngleDeg: number, segments: Segment[]): Point {
  const base = baseDir(baseAngleDeg)
  const offset = GEOM.supportLabelOffset
  const clearance = GEOM.bodyHalfWidth + LETTER_RADIUS

  // Away from the glyph, then most-opposite the base first.
  const dirs = COMPASS.filter((d) => d.x * base.x + d.y * base.y < GLYPH_CONE).sort(
    (a, b) => (b.x * -base.x + b.y * -base.y) - (a.x * -base.x + a.y * -base.y),
  )

  for (const ring of RINGS) {
    for (const d of dirs) {
      const p = { x: at.x + d.x * offset * ring, y: at.y + d.y * offset * ring }
      if (segments.every((s) => distanceToSegment(p, s) >= clearance)) return p
    }
  }

  // Nothing clears — fall back to straight out from the base, which is at least
  // predictable, and let the letter overlap.
  return { x: at.x - base.x * offset, y: at.y - base.y * offset }
}
