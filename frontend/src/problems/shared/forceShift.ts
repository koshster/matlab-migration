/**
 * drawForces.m:60-98 — an arrow whose direction runs straight into structure is
 * slid back a full arrow length so its tip lands on the anchor rather than its
 * tail, which keeps the shaft off the member it would otherwise lie along.
 *
 * Truss and rigid body both need this, and both had their own copy: the only
 * difference was where the segment list came from (members vs. body path
 * vertices), so that is the one thing the caller supplies.
 */

export interface Segment {
  from: { x: number; y: number }
  to: { x: number; y: number }
}

/**
 * Direction cosine above which a segment counts as "in the way" of a force.
 * MATLAB tests for structure in exactly that grid direction, so the threshold
 * has to be tight enough that a 45-degree diagonal (0.707) does not read as
 * blocking.
 */
const BLOCKED_DOT = 0.9

const key = (x: number, y: number): string => `${String(x)},${String(y)}`

/**
 * Whether an arrow anchored at a point and pointing along a unit vector should
 * be drawn shifted. Built once per diagram, then queried per force.
 */
export type ShiftRule = (at: { x: number; y: number }, ux: number, uy: number) => boolean

export function buildShiftRule(segments: Segment[]): ShiftRule {
  const incident = new Map<string, Array<[number, number]>>()

  const push = (k: string, dir: [number, number]) => {
    const list = incident.get(k)
    if (list) list.push(dir)
    else incident.set(k, [dir])
  }

  for (const { from, to } of segments) {
    const dx = to.x - from.x
    const dy = to.y - from.y
    const len = Math.hypot(dx, dy)
    if (len < 1e-9) continue
    const ux = dx / len
    const uy = dy / len
    push(key(from.x, from.y), [ux, uy])
    push(key(to.x, to.y), [-ux, -uy])
  }

  return (at, ux, uy) => {
    const dirs = incident.get(key(at.x, at.y))
    if (!dirs) return false
    const forwardBlocked = dirs.some(([mx, my]) => mx * ux + my * uy > BLOCKED_DOT)
    if (!forwardBlocked) return false
    // Only shift if the far side is actually clear, otherwise we trade one
    // overlap for another.
    return !dirs.some(([mx, my]) => -(mx * ux + my * uy) > BLOCKED_DOT)
  }
}

/** Consecutive vertex pairs of each polyline, as segments. */
export function pathSegments(paths: Array<Array<{ x: number; y: number }>>): Segment[] {
  const out: Segment[] = []
  for (const pts of paths) {
    for (let i = 0; i < pts.length - 1; i++) out.push({ from: pts[i], to: pts[i + 1] })
  }
  return out
}
