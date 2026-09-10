import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import BodyPipes from './BodyPipes'
import MathLabel, { splitQuantity } from './MathLabel'
import { COLORS, GEOM, TYPE } from './constants'
import { buildShiftRule, pathSegments, type Segment } from './forceShift'
import { baseDir } from './supportGeometry'
import { placeSupportLabel } from './supportLabels'

/**
 * Covers the primitives the truss and rigid-body renderers share, so the two
 * cannot drift back apart: the deck (docs/Images.pptx) draws both modules with
 * one visual language and these are the pieces that language lives in.
 */

describe('splitQuantity', () => {
  it.each([
    ['F', '', 'F'],
    ['3F', '3', 'F'],
    ['-2a', '-2', 'a'],
    ['2a', '2', 'a'],
    ['0', '0', ''],
    ['A', '', 'A'],
  ])('splits %s into an upright multiplier and an italic symbol', (label, head, symbol) => {
    expect(splitQuantity(label)).toEqual({ head, symbol })
  })

  it('italicises the whole symbol of a couple label, not just a trailing F', () => {
    // Regression: couple labels are "4Fa", and a trailing-F-only rule left the
    // entire string upright, so moments read differently from every force.
    expect(splitQuantity('4Fa')).toEqual({ head: '4', symbol: 'Fa' })
  })

  it('renders the multiplier upright and the symbol italic', () => {
    const { container } = render(
      <svg>
        <MathLabel x={0} y={0} label="4Fa" fontSize={0.2} fill="#000" />
      </svg>,
    )
    const text = container.querySelector('text')
    expect(text?.textContent).toBe('4Fa')
    const italic = container.querySelector('tspan[font-style="italic"]')
    expect(italic?.textContent).toBe('Fa')
  })
})

describe('baseDir', () => {
  it.each([
    [0, 0, -1],
    [90, 1, 0],
    [180, 0, 1],
    [270, -1, 0],
  ])('points a rotation-%i base at (%i, %i)', (angle, x, y) => {
    const d = baseDir(angle)
    expect(d.x).toBeCloseTo(x, 10)
    expect(d.y).toBeCloseTo(y, 10)
  })

  it('returns exact zeros on the axes so downstream ties break deterministically', () => {
    // Math.cos(1.5 * Math.PI) is -1.8e-16; unsnapped, that noise silently
    // decided which side a support letter landed on.
    expect(baseDir(270).y).toBe(0)
    expect(baseDir(180).x).toBe(0)
  })
})

describe('BodyPipes', () => {
  const square = [
    { x: 0, y: 0 },
    { x: 1, y: 0 },
    { x: 1, y: 1 },
  ]

  it('strokes the body at the deck body width, not the truss member width', () => {
    const { container } = render(
      <svg>
        <BodyPipes paths={[square]} />
      </svg>,
    )
    const lines = [...container.querySelectorAll('polyline')]
    const face = lines.find((l) => l.getAttribute('stroke') === COLORS.member)
    expect(Number(face?.getAttribute('stroke-width'))).toBeCloseTo(GEOM.bodyHalfWidth * 2, 10)
  })

  it('keeps the outline a hairline so the bar does not read as a black slab', () => {
    const { container } = render(
      <svg>
        <BodyPipes paths={[square]} />
      </svg>,
    )
    const edge = [...container.querySelectorAll('polyline')].find(
      (l) => l.getAttribute('stroke') === COLORS.outline,
    )
    const edgeWidth = Number(edge?.getAttribute('stroke-width'))
    expect(edgeWidth - GEOM.bodyHalfWidth * 2).toBeCloseTo(GEOM.outlineWidth * 2, 10)
  })

  it('draws every outline before any fill so crossing runs read as one body', () => {
    // A body is often several runs (the "+" in ppt/media/image2.png is two).
    // Outlining and filling one run at a time leaves the second run's edge
    // painted across the first run's face.
    const { container } = render(
      <svg>
        <BodyPipes
          paths={[
            square,
            [
              { x: 0.5, y: -1 },
              { x: 0.5, y: 2 },
            ],
          ]}
        />
      </svg>,
    )
    const strokes = [...container.querySelectorAll('polyline')].map((l) => l.getAttribute('stroke'))
    expect(strokes).toEqual([COLORS.outline, COLORS.outline, COLORS.member, COLORS.member])
  })

  it('skips a run that cannot be drawn instead of emitting a degenerate polyline', () => {
    const { container } = render(
      <svg>
        <BodyPipes paths={[[{ x: 0, y: 0 }], []]} />
      </svg>,
    )
    expect(container.querySelectorAll('polyline')).toHaveLength(0)
  })
})

describe('placeSupportLabel', () => {
  /** Same clearance the placer uses: half the bar plus half the letter. */
  const clearance = GEOM.bodyHalfWidth + TYPE.supportLabel * 0.6

  function distanceToSegment(p: { x: number; y: number }, { from, to }: Segment): number {
    const dx = to.x - from.x
    const dy = to.y - from.y
    const lenSq = dx * dx + dy * dy
    if (lenSq === 0) return Math.hypot(p.x - from.x, p.y - from.y)
    const t = Math.min(Math.max(((p.x - from.x) * dx + (p.y - from.y) * dy) / lenSq, 0), 1)
    return Math.hypot(p.x - (from.x + t * dx), p.y - (from.y + t * dy))
  }

  it('offsets straight out from the base when that side is clear', () => {
    // The common case, and what the deck shows for both letters in image6.
    const bar: Segment[] = [{ from: { x: -1, y: 0 }, to: { x: 0, y: 0 } }]
    const at = placeSupportLabel({ x: 0, y: 0 }, 0, bar)
    expect(at.x).toBeCloseTo(0, 10)
    expect(at.y).toBeCloseTo(GEOM.supportLabelOffset, 10)
  })

  it('steps off the straight-out direction when a bar occupies it', () => {
    // ppt/media/image34.png: the support at the elbow (a,a) faces left, so
    // "straight out" is along the top member. The deck sets `A` diagonally out
    // from the corner instead.
    const elbow: Segment[] = pathSegments([
      [
        { x: 1, y: 0 },
        { x: 1, y: 1 },
        { x: 2, y: 1 },
      ],
    ])
    const at = placeSupportLabel({ x: 1, y: 1 }, 270, elbow)
    expect(at.x).toBeGreaterThan(1)
    expect(at.y).toBeGreaterThan(1)
    for (const s of elbow) expect(distanceToSegment(at, s)).toBeGreaterThanOrEqual(clearance)
  })

  it('never lands the letter on the support glyph itself', () => {
    // The glyph sits on the base side, so the letter must not go there.
    for (const angle of [0, 90, 180, 270]) {
      const at = placeSupportLabel({ x: 0, y: 0 }, angle, [])
      const base = baseDir(angle)
      expect(at.x * base.x + at.y * base.y).toBeLessThan(0)
    }
  })

  it('clears every bar of a mid-span support on a closed loop', () => {
    // A support can attach part-way along a run rather than at a vertex, which
    // a vertex-incidence rule would miss entirely.
    const loop = pathSegments([
      [
        { x: 0, y: 0 },
        { x: 2, y: 0 },
        { x: 2, y: 2 },
        { x: 0, y: 2 },
        { x: 0, y: 0 },
      ],
    ])
    const at = placeSupportLabel({ x: 1, y: 0 }, 0, loop)
    for (const s of loop) expect(distanceToSegment(at, s)).toBeGreaterThanOrEqual(clearance)
  })

  it('still returns a finite point when the support is boxed in', () => {
    // Degenerate geometry should cost placement quality, not crash the diagram.
    const boxed = pathSegments([
      [
        { x: -1, y: 0 },
        { x: 1, y: 0 },
      ],
      [
        { x: 0, y: -1 },
        { x: 0, y: 1 },
      ],
    ])
    const at = placeSupportLabel({ x: 0, y: 0 }, 0, boxed)
    expect(Number.isFinite(at.x)).toBe(true)
    expect(Number.isFinite(at.y)).toBe(true)
  })
})

describe('buildShiftRule', () => {
  const bar = [{ from: { x: 0, y: 0 }, to: { x: 1, y: 0 } }]

  it('shifts an arrow that would lie along the structure', () => {
    expect(buildShiftRule(bar)({ x: 0, y: 0 }, 1, 0)).toBe(true)
  })

  it('leaves an arrow alone when its direction is clear', () => {
    expect(buildShiftRule(bar)({ x: 0, y: 0 }, 0, 1)).toBe(false)
  })

  it('does not shift when both sides are blocked, which would just move the overlap', () => {
    const through = [
      { from: { x: -1, y: 0 }, to: { x: 0, y: 0 } },
      { from: { x: 0, y: 0 }, to: { x: 1, y: 0 } },
    ]
    expect(buildShiftRule(through)({ x: 0, y: 0 }, 1, 0)).toBe(false)
  })

  it('does not treat a 45-degree diagonal as blocking', () => {
    const diagonal = [{ from: { x: 0, y: 0 }, to: { x: 1, y: 1 } }]
    expect(buildShiftRule(diagonal)({ x: 0, y: 0 }, 1, 0)).toBe(false)
  })

  it('ignores zero-length segments rather than dividing by zero', () => {
    const rule = buildShiftRule([{ from: { x: 0, y: 0 }, to: { x: 0, y: 0 } }])
    expect(rule({ x: 0, y: 0 }, 1, 0)).toBe(false)
  })
})
