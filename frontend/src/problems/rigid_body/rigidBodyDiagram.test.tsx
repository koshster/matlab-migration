import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import RigidBodyDiagram from './RigidBodyDiagram'
import { fixtures } from './fixtures'
import { getRenderer } from '../registry'

/**
 * Fixture provenance (see fixtures.ts):
 *   pin_roller      seed 42, support_case 2
 *   three_rollers   seed  7, support_case 1
 *   cantilever_wall seed 11, support_case 3
 *   with_moments    seed  3, support_case 2, num_moments 2, num_loads 2
 */

function draw(geometry: unknown): SVGSVGElement {
  const { container } = render(<RigidBodyDiagram geometry={geometry} />)
  const svg = container.querySelector('svg')
  if (!svg) throw new Error('no svg rendered')
  return svg
}

function viewBox(svg: SVGSVGElement): [number, number, number, number] {
  const parts = (svg.getAttribute('viewBox') ?? '').split(/\s+/).map(Number)
  expect(parts).toHaveLength(4)
  return [parts[0], parts[1], parts[2], parts[3]]
}

describe('RigidBodyDiagram', () => {
  it('is what the registry hands back for rigid_body', () => {
    expect(getRenderer('rigid_body')).not.toBe(getRenderer('definitely-not-a-type'))
  })

  it('draws every element kind the generator emits', () => {
    const svg = draw(fixtures.with_moments)

    // Body: 2 polylines per path (outline pass + fill pass).
    expect(svg.querySelectorAll('polyline')).toHaveLength(2)
    // Polygons: pin triangle + roller triangle + 2 force 7-gons + 2 moment arrowheads.
    expect(svg.querySelectorAll('polygon')).toHaveLength(6)
    // Forces use filled polygons (no <line>); moments use <path> arcs, not purple.
    expect(svg.querySelectorAll('line[stroke="#dc2626"]')).toHaveLength(0)
    expect(svg.querySelectorAll('path[stroke="#8B0000"]')).toHaveLength(2)
    // Roller wheel circle; joint markers removed (rigid body has no discrete joints).
    expect(svg.querySelectorAll('circle').length).toBeGreaterThanOrEqual(1)
  })

  it('labels supports so the diagram ties back to the answer fields', () => {
    // A student answering reaction_Ax has to be able to find A in the picture.
    const svg = draw(fixtures.three_rollers)
    const labels = [...svg.querySelectorAll('text')].map((t) => t.textContent)
    expect(labels).toEqual(expect.arrayContaining(['A', 'B', 'C']))
  })

  it.each(Object.entries(fixtures))('fits the whole body in view: %s', (_name, geometry) => {
    const svg = draw(geometry)
    const [vx, vy, vw, vh] = viewBox(svg)

    const points = svg.querySelector('polyline')?.getAttribute('points') ?? ''
    const pairs = points.split(' ').map((p) => p.split(',').map(Number))
    expect(pairs.length).toBeGreaterThan(1)

    for (const [x, y] of pairs) {
      expect(x).toBeGreaterThanOrEqual(vx)
      expect(x).toBeLessThanOrEqual(vx + vw)
      // The scene is drawn inside a scale(1,-1) flip, so a physics y maps to -y.
      expect(-y).toBeGreaterThanOrEqual(vy)
      expect(-y).toBeLessThanOrEqual(vy + vh)
    }
  })

  it('places body nodes at their raw grid coordinates without rescaling', () => {
    // Generator produces integer-grid coordinates; the renderer uses plotWindow
    // (floor/ceil ±1) rather than rescaling, so coordinates stay unchanged.
    const svg = draw(fixtures.pin_roller)
    const pairs = (svg.querySelector('polyline')?.getAttribute('points') ?? '')
      .split(' ')
      .map((p) => p.split(',').map(Number))
    expect(pairs.length).toBeGreaterThan(1)
    for (const [x, y] of pairs) {
      expect(Number.isInteger(x)).toBe(true)
      expect(Number.isInteger(y)).toBe(true)
    }
  })

  describe('support orientation', () => {
    /**
     * Guards the convention this renderer originally got backwards.
     *
     * `good_pin_support_orientation` accepts rotation 90 only when nothing
     * extends to +x, so 90 means the base sits to the RIGHT -- the opposite of
     * what the docstring beside it claims. Drawing it the docstring's way put
     * the support through the body on roughly a third of generated problems.
     */
    const expected: Record<number, [number, number]> = {
      0: [0, -1],
      90: [1, 0],
      180: [0, 1],
      270: [-1, 0],
    }

    it.each([0, 90, 180, 270])('puts a rotation-%i pin base on the free side', (rotation) => {
      const svg = draw({
        schemaVersion: 1,
        elements: [{ element_type: 'pin', properties: { position: [0, 0], rotation, label: 'A' } }],
      })

      const rotated = [...svg.querySelectorAll('g')].find((g) =>
        (g.getAttribute('transform') ?? '').includes('rotate'),
      )
      const match = /rotate\((-?[\d.]+)\)/.exec(rotated?.getAttribute('transform') ?? '')
      expect(match).not.toBeNull()

      const angle = ((Number(match?.[1]) % 360) + 360) % 360
      const rad = (angle * Math.PI) / 180
      // The glyph is authored base-down, so the drawn base direction is (0,-1)
      // turned counter-clockwise by the rendered angle.
      const direction = [Math.sin(rad), -Math.cos(rad)]

      expect(direction[0]).toBeCloseTo(expected[rotation][0], 5)
      expect(direction[1]).toBeCloseTo(expected[rotation][1], 5)
    })

    it('flips a wall so its hatching faces away from the body', () => {
      // A cantilever's rotation points along the body, not at the free side.
      const svg = draw({
        schemaVersion: 1,
        elements: [
          { element_type: 'wall', properties: { position: [0, 0], rotation: 0, label: 'A' } },
        ],
      })
      const rotated = [...svg.querySelectorAll('g')].find((g) =>
        (g.getAttribute('transform') ?? '').includes('rotate'),
      )
      expect(rotated?.getAttribute('transform')).toContain('rotate(180)')
    })
  })

  describe('malformed payloads', () => {
    it('falls back to a message rather than an empty frame', () => {
      const { container } = render(<RigidBodyDiagram geometry={{ elements: [] }} />)
      expect(container.textContent).toMatch(/no diagram/i)
    })

    it.each([null, undefined, 42, 'nonsense', {}, { elements: 'not-an-array' }])(
      'survives %s',
      (geometry) => {
        const { container } = render(<RigidBodyDiagram geometry={geometry} />)
        expect(container.textContent).toMatch(/no diagram/i)
      },
    )

    it('drops a single bad element without losing the rest', () => {
      const svg = draw({
        schemaVersion: 1,
        elements: [
          { element_type: 'rigid_body_path', properties: { path: [[0, 0], [1, 0], [1, 1]] } },
          { element_type: 'pin', properties: { position: 'not-a-point', rotation: 0 } },
          { element_type: 'point_load', properties: { position: [1, 1], force_vector: null } },
        ],
      })
      // 2 polylines (outline + fill) for the valid rigid_body_path.
      expect(svg.querySelectorAll('polyline')).toHaveLength(2)
      expect(svg.querySelectorAll('polygon')).toHaveLength(0)
      expect(svg.querySelectorAll('line[stroke="#dc2626"]')).toHaveLength(0)
    })

    it('does not divide by zero on a degenerate body', () => {
      const svg = draw({
        schemaVersion: 1,
        elements: [{ element_type: 'rigid_body_path', properties: { path: [[2, 2], [2, 2]] } }],
      })
      for (const value of viewBox(svg)) expect(Number.isFinite(value)).toBe(true)
    })
  })

  it('gives each diagram a unique title id so aria is correct across diagrams', () => {
    // Review mode renders several problems at once; shared title ids would break
    // aria-labelledby on all but the first. useId() inside the component fixes this.
    const { container } = render(
      <>
        <RigidBodyDiagram geometry={fixtures.pin_roller} />
        <RigidBodyDiagram geometry={fixtures.three_rollers} />
      </>,
    )
    const ids = [...container.querySelectorAll('title')].map((t) => t.getAttribute('id'))
    expect(ids.length).toBeGreaterThan(1)
    expect(new Set(ids).size).toBe(ids.length)
  })
})
