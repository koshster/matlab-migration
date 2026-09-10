import { GEOM, TYPE } from '../shared/constants'

export interface Placement {
  x: number
  y: number
  anchor: 'start' | 'middle' | 'end'
}

interface Pt {
  x: number
  y: number
}

interface Seg {
  id: number
  a: Pt
  b: Pt
}

/** Roughly half the height of a label glyph, used as the collision radius. */
const LABEL_RADIUS = TYPE.memberLabel * 0.55
/** A candidate this far from other ink is considered fine as-is. */
const GOOD_CLEARANCE = GEOM.memberHalfWidth + LABEL_RADIUS + 0.02
/** Only switch sides if the alternative is meaningfully roomier. */
const SWITCH_MARGIN = 0.02
/**
 * Two labels closer than this read as one blob. Tuned against real 8-node
 * generator output: the reference 3-6 node trusses keep their labels >= 0.45
 * apart, so this only fires on the dense cases.
 */
const LABEL_SEPARATION = TYPE.memberLabel * 2.3

function distToSegment(p: Pt, a: Pt, b: Pt): number {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const l2 = dx * dx + dy * dy
  if (l2 === 0) return Math.hypot(p.x - a.x, p.y - a.y)
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2
  t = Math.max(0, Math.min(1, t))
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
}

function clearance(p: Pt, segs: Seg[], selfId: number, nodes: Pt[]): number {
  let min = Infinity
  for (const n of nodes) min = Math.min(min, Math.hypot(p.x - n.x, p.y - n.y))
  for (const s of segs) {
    if (s.id === selfId) continue
    min = Math.min(min, distToSegment(p, s.a, s.b))
  }
  return min
}

/**
 * Where each member number sits.
 *
 * The first choice is MATLAB's rule (plotTruss.m:60-66): horizontal members
 * label straight up, everything else offsets along the CCW perpendicular of
 * from->to. That rule alone is fine for the 3-6 node trusses in the reference
 * slides, but at 8 nodes / 13 members it can drop a number on top of a
 * neighbouring member or another number, so a candidate is mirrored to the far
 * side when the near side is crowded and the far side is clearly roomier.
 */
export function placeMemberLabels(
  members: Array<{ id: number; from: Pt; to: Pt }>,
  nodes: Pt[],
): Map<number, Placement> {
  const segs: Seg[] = members.map((m) => ({ id: m.id, a: m.from, b: m.to }))
  const out = new Map<number, Placement>()
  const placed: Pt[] = []
  const off = GEOM.memberLabelOffset

  for (const m of members) {
    const dx = m.to.x - m.from.x
    const dy = m.to.y - m.from.y
    const len = Math.hypot(dx, dy) || 1
    const px = -dy / len
    const py = dx / len
    const mx = (m.from.x + m.to.x) / 2
    const my = (m.from.y + m.to.y) / 2
    const horizontal = Math.abs(dy / len) < 1e-6

    const primary: Placement = horizontal
      ? { x: mx, y: my + off, anchor: 'start' }
      : { x: mx + off * px, y: my + off * py, anchor: px < 0 ? 'end' : 'start' }
    const mirror: Placement = horizontal
      ? { x: mx, y: my - off, anchor: 'start' }
      : { x: mx - off * px, y: my - off * py, anchor: px < 0 ? 'start' : 'end' }

    const cp = clearance(primary, segs, m.id, nodes)
    const cm = clearance(mirror, segs, m.id, nodes)

    let chosen = primary
    let chosenClear = cp
    if (cp < GOOD_CLEARANCE && cm > cp + SWITCH_MARGIN) {
      chosen = mirror
      chosenClear = cm
    }

    // Second pass over labels already placed: a collision there also warrants a
    // flip, as long as the other side is not itself crowded.
    const crowded = (p: Pt) => placed.some((q) => Math.hypot(p.x - q.x, p.y - q.y) < LABEL_SEPARATION)
    if (crowded(chosen)) {
      const other = chosen === primary ? mirror : primary
      const otherClear = chosen === primary ? cm : cp
      if (!crowded(other) && otherClear > chosenClear - SWITCH_MARGIN) chosen = other
    }

    out.set(m.id, chosen)
    placed.push(chosen)
  }
  return out
}
