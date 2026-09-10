import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { getRenderer } from '../registry'
import TrussDiagram from './TrussDiagram'
import { COLORS, GEOM, OPACITY } from './constants'
import threeNode from '@statics/contract/fixtures/truss-3node.json'
import fourNode from '@statics/contract/fixtures/truss-4node.json'
import sixNode from '@statics/contract/fixtures/truss-6node.json'

const FIXTURES = {
  'truss-3node': threeNode.geometry,
  'truss-4node': fourNode.geometry,
  'truss-6node': sixNode.geometry,
} as unknown as Record<string, unknown>

function draw(geometry: unknown): SVGSVGElement {
  const { container } = render(<TrussDiagram geometry={geometry} />)
  const svg = container.querySelector('svg')
  if (!svg) throw new Error('no svg rendered')
  return svg
}

function viewBox(svg: SVGSVGElement): [number, number, number, number] {
  const parts = (svg.getAttribute('viewBox') ?? '').split(/\s+/).map(Number)
  expect(parts).toHaveLength(4)
  return [parts[0], parts[1], parts[2], parts[3]]
}

function texts(svg: SVGSVGElement): string[] {
  return [...svg.querySelectorAll('text')].map((t) => t.textContent)
}

/** Every x,y pair drawn as a polygon vertex, in physics coordinates. */
function polygonPoints(svg: SVGSVGElement): Array<[number, number]> {
  return [...svg.querySelectorAll('polygon')].flatMap((p) =>
    (p.getAttribute('points') ?? '')
      .trim()
      .split(/\s+/)
      .map((pair) => pair.split(',').map(Number) as [number, number]),
  )
}

/** Minimal hand-built geometry; the shipped fixtures never rotate a support. */
function geometry(overrides: {
  nodes: Array<{ id: number; x: number; y: number }>
  members?: Array<{ id: number; from: number; to: number }>
  supports?: Array<{ node: number; type: 'pin' | 'roller'; angleDeg: number }>
  forces?: Array<{ node: number; fx: number; fy: number; label: string }>
}) {
  return {
    schemaVersion: 1,
    nodes: overrides.nodes,
    members: (overrides.members ?? []).map((m) => ({ ...m, label: `S${String(m.id)}` })),
    supports: overrides.supports ?? [],
    forces: overrides.forces ?? [],
    bounds: { xMin: 0, xMax: 0, yMin: 0, yMax: 0 },
  }
}

describe('TrussDiagram', () => {
  it('is what the registry hands back for truss', () => {
    expect(getRenderer('truss')).not.toBe(getRenderer('definitely-not-a-type'))
  })

  it.each(Object.entries(FIXTURES))('renders %s', (_name, g) => {
    const svg = draw(g)
    expect(svg.querySelectorAll('polygon').length).toBeGreaterThan(0)
  })

  it('numbers members 1..n in the diagram and never shows the S-subscript key', () => {
    // S₁ is the AnswerPanel caption (assignments.py::_member_label); the diagram
    // carries the bare number, as in the reference figures.
    const svg = draw(FIXTURES['truss-6node'])
    const labels = texts(svg)
    for (const n of ['1', '2', '3', '4', '5', '6', '7', '8', '9']) {
      expect(labels).toContain(n)
    }
    expect(labels.join('')).not.toMatch(/S/)
  })

  it('offsets a horizontal member label above the member', () => {
    const svg = draw(
      geometry({
        nodes: [
          { id: 1, x: 0, y: 0 },
          { id: 2, x: 2, y: 0 },
        ],
        members: [{ id: 1, from: 1, to: 2 }],
      }),
    )
    const label = svg.querySelector(`text[fill="${COLORS.memberLabel}"]`)
    expect(label?.textContent).toBe('1')
    expect(label?.parentElement?.getAttribute('transform')).toBe(
      `translate(1,${String(GEOM.memberLabelOffset)}) scale(1,-1)`,
    )
  })

  it('leaves the arrow tail on the node when the force points into open space', () => {
    // Reference ppt/media/image35.png: the upward 5F sits above its node.
    const svg = draw(
      geometry({
        nodes: [
          { id: 1, x: 0, y: 0 },
          { id: 2, x: 1, y: 0 },
        ],
        members: [{ id: 1, from: 1, to: 2 }],
        forces: [{ node: 1, fx: 0, fy: 1, label: 'F' }],
      }),
    )
    const tip = polygonPoints(svg).find(([, y]) => Math.abs(y - GEOM.arrowLength) < 1e-9)
    expect(tip).toBeDefined()
  })

  it('slides the arrow so its tip lands on the node when the force points into structure', () => {
    // Reference ppt/media/image36.png: the downward 3F is drawn above its node.
    const svg = draw(
      geometry({
        nodes: [
          { id: 1, x: 0, y: 0 },
          { id: 2, x: 0, y: -1 },
        ],
        members: [{ id: 1, from: 1, to: 2 }],
        forces: [{ node: 1, fx: 0, fy: -1, label: '3F' }],
      }),
    )
    // Tail is one arrow length above the node, so nothing is drawn below y = 0.
    const arrow = polygonPoints(svg).filter(([x]) => Math.abs(x) < 0.05)
    expect(Math.max(...arrow.map(([, y]) => y))).toBeCloseTo(GEOM.arrowLength, 6)
    expect(Math.min(...arrow.map(([, y]) => y))).toBeCloseTo(0, 6)
  })

  it.each([
    [0, 0, -1],
    [90, 1, 0],
    [180, 0, 1],
    [270, -1, 0],
  ])('points a support base outward for angleDeg %i', (angleDeg, ex, ey) => {
    const svg = draw(
      geometry({
        nodes: [{ id: 1, x: 0, y: 0 }],
        supports: [{ node: 1, type: 'pin', angleDeg }],
      }),
    )
    const tri = [...svg.querySelectorAll('polygon')].find(
      (p) => p.getAttribute('fill') === COLORS.pinFill,
    )
    const frame = tri?.parentElement?.getAttribute('transform') ?? ''
    expect(frame).toBe(`translate(0,0) rotate(${String(angleDeg)})`)

    // Sanity-check the unrotated glyph really does hang below the node.
    const pts = (tri?.getAttribute('points') ?? '').split(' ').map((p) => p.split(',').map(Number))
    const base = pts.filter(([, y]) => y < 0)
    expect(base).toHaveLength(2)
    expect(ex * ex + ey * ey).toBe(1)
  })

  it('draws the roller wheel and the shorter roller ground bar', () => {
    const svg = draw(
      geometry({
        nodes: [{ id: 1, x: 0, y: 0 }],
        supports: [{ node: 1, type: 'roller', angleDeg: 0 }],
      }),
    )
    const wheel = [...svg.querySelectorAll('circle')].find(
      (c) => c.getAttribute('fill') === COLORS.wheelFill,
    )
    expect(wheel?.getAttribute('cy')).toBe(String(GEOM.wheelCenterY))
    const bar = svg.querySelector(`rect[fill="${COLORS.ground}"]`)
    expect(bar?.getAttribute('width')).toBe(String(GEOM.rollerBarHalfLength * 2))
  })

  it('draws no hatch ticks under a support', () => {
    const svg = draw(FIXTURES['truss-3node'])
    expect(svg.querySelectorAll('line[stroke="#6b7280"]')).toHaveLength(0)
  })

  it('labels the grid in units of a', () => {
    const svg = draw(FIXTURES['truss-3node'])
    const labels = texts(svg)
    expect(labels).toContain('0')
    expect(labels).toContain('a')
    expect(labels).toContain('-a')
  })

  it('snaps the plot window to whole grid squares', () => {
    const svg = draw(FIXTURES['truss-6node'])
    const [vx, vy, vw, vh] = viewBox(svg)
    // Margins are the only fractional part; the window itself is integral.
    expect(Number.isInteger(vx + 0.62)).toBe(true)
    expect(Number.isInteger(-(vy + 0.16))).toBe(true)
    expect(Number.isInteger(vw - 0.78)).toBe(true)
    expect(Number.isInteger(vh - 0.66)).toBe(true)
  })

  it('renders an unlabelled force as an arrow with no text', () => {
    // truss-4node ships one force with label "".
    const svg = draw(FIXTURES['truss-4node'])
    expect(texts(svg)).not.toContain('')
    expect(svg.querySelectorAll(`polygon[fill="${COLORS.force}"]`)).toHaveLength(2)
  })

  it.each(Object.entries(FIXTURES))('keeps everything it draws inside the viewBox: %s', (_n, g) => {
    const svg = draw(g)
    const [vx, vy, vw, vh] = viewBox(svg)
    for (const [x, y] of polygonPoints(svg)) {
      // Physics y is up, SVG y is down.
      expect(x).toBeGreaterThanOrEqual(vx)
      expect(x).toBeLessThanOrEqual(vx + vw)
      expect(-y).toBeGreaterThanOrEqual(vy)
      expect(-y).toBeLessThanOrEqual(vy + vh)
    }
  })

  describe('layering', () => {
    // A support triangle or an arrow shaft landing on a member has to stay
    // readable, so the structure goes to the back and the annotations to the
    // front -- at slightly reduced opacity so the member underneath still shows.
    const overlapping = geometry({
      nodes: [
        { id: 1, x: 0, y: 0 },
        { id: 2, x: 2, y: 0 },
        { id: 3, x: 1, y: 1 },
      ],
      members: [
        { id: 1, from: 1, to: 2 },
        { id: 2, from: 1, to: 3 },
        { id: 3, from: 2, to: 3 },
      ],
      supports: [
        { node: 1, type: 'pin', angleDeg: 0 },
        { node: 2, type: 'roller', angleDeg: 0 },
      ],
      forces: [{ node: 3, fx: 0, fy: -1, label: '2F' }],
    })

    it('paints members behind supports, and supports behind force arrows', () => {
      const svg = draw(overlapping)
      const order = [...svg.querySelectorAll('polygon')].map((el) => el.getAttribute('fill'))

      const last = (fill: string) => order.lastIndexOf(fill)
      const first = (fill: string) => order.indexOf(fill)

      expect(first(COLORS.member)).toBeGreaterThanOrEqual(0)
      expect(first(COLORS.pinFill)).toBeGreaterThan(last(COLORS.member))
      expect(first(COLORS.force)).toBeGreaterThan(last(COLORS.rollerFill))
    })

    it('lets the structure show through supports and arrows', () => {
      const svg = draw(overlapping)

      const supportGroups = [...svg.querySelectorAll('g')].filter((el) =>
        (el.getAttribute('transform') ?? '').includes('rotate'),
      )
      expect(supportGroups).toHaveLength(2)
      for (const g of supportGroups) {
        expect(Number(g.getAttribute('opacity'))).toBe(OPACITY.support)
      }

      const arrow = svg.querySelector(`polygon[fill="${COLORS.force}"]`)
      expect(Number(arrow?.getAttribute('opacity'))).toBe(OPACITY.force)
    })

    it('keeps the force label fully opaque', () => {
      // The number a student has to read must not be dimmed.
      const svg = draw(overlapping)
      const label = [...svg.querySelectorAll('text')].find((t) => t.textContent === '2F')
      expect(label).toBeDefined()
      expect(label?.getAttribute('opacity')).toBeNull()
      expect(label?.closest('[opacity]')).toBeNull()
    })
  })
})
