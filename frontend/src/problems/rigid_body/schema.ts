/**
 * Narrowing helpers for the generic element-list geometry payload.
 *
 * Unlike truss, this domain arrives as an untyped `{ schemaVersion, elements }`
 * blob -- the contract calls `geometry` "opaque to the shell, typed per
 * problemType by the renderer", so the typing happens here. Every accessor
 * returns a fallback instead of throwing: a malformed element should cost one
 * glyph, not the whole diagram.
 */

export interface Point {
  x: number
  y: number
}

export interface RawElement {
  element_type: string
  properties: Record<string, unknown>
}

export interface RigidBodyGeometry {
  schemaVersion: number
  elements: RawElement[]
}

export function parseGeometry(geometry: unknown): RawElement[] {
  if (typeof geometry !== 'object' || geometry === null) return []
  const elements = (geometry as { elements?: unknown }).elements
  if (!Array.isArray(elements)) return []
  return elements.filter((el): el is RawElement => {
    if (typeof el !== 'object' || el === null) return false
    const candidate = el as { element_type?: unknown; properties?: unknown }
    return (
      typeof candidate.element_type === 'string' &&
      typeof candidate.properties === 'object' &&
      candidate.properties !== null
    )
  })
}

export function num(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function str(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

/** `[x, y]` pair, as emitted for `position`, `force_vector` and path vertices. */
export function point(value: unknown): Point | null {
  if (!Array.isArray(value) || value.length < 2) return null
  // `Array.isArray` on an `unknown` widens the elements to `any`; re-narrowing
  // to `unknown[]` keeps the typeof checks below actually meaningful.
  const pair: unknown[] = value
  const x = pair[0]
  const y = pair[1]
  if (typeof x !== 'number' || typeof y !== 'number') return null
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null
  return { x, y }
}

export function path(value: unknown): Point[] {
  if (!Array.isArray(value)) return []
  return value.map(point).filter((p): p is Point => p !== null)
}

/**
 * Every point the diagram will draw, for fitting the viewBox.
 *
 * Support and load glyphs stick out past their anchor, but they are a fixed
 * size in diagram units, so the padding in `RigidBodyDiagram` covers them
 * rather than each one being measured here.
 */
export function collectPoints(elements: RawElement[]): Point[] {
  const points: Point[] = []
  for (const el of elements) {
    const p = el.properties
    if (el.element_type === 'rigid_body_path') {
      points.push(...path(p.path))
    } else if (el.element_type === 'node') {
      points.push({ x: num(p.x), y: num(p.y) })
    } else {
      const at = point(p.position)
      if (at) points.push(at)
    }
  }
  return points
}
