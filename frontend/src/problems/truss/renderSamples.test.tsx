import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, it } from 'vitest'
import TrussDiagram from './TrussDiagram'

/**
 * Dev-only harness: writes standalone HTML for geometries transcribed from the
 * reference slides in `docs/Images.pptx`, so a render can be screenshotted and
 * compared side by side with the originals. Skipped unless TRUSS_RENDER_OUT is
 * set, so it is inert in CI.
 *
 *   TRUSS_RENDER_OUT=/tmp/truss node_modules/.bin/vitest run src/problems/truss/renderSamples.test.tsx
 */
const OUT = process.env.TRUSS_RENDER_OUT
/** Optional JSON file of `{ name: TrussGeometry }` — e.g. real generator output. */
const EXTRA = process.env.TRUSS_RENDER_EXTRA

interface Sample {
  name: string
  geometry: {
    schemaVersion: 1
    nodes: Array<{ id: number; x: number; y: number }>
    members: Array<{ id: number; from: number; to: number; label: string }>
    supports: Array<{ node: number; type: 'pin' | 'roller'; angleDeg: number }>
    forces: Array<{ node: number; fx: number; fy: number; label: string }>
    bounds: { xMin: number; xMax: number; yMin: number; yMax: number }
  }
}

const bounds = { xMin: 0, xMax: 0, yMin: 0, yMax: 0 }
const member = (id: number, from: number, to: number) => ({ id, from, to, label: `S${String(id)}` })

const SAMPLES: Sample[] = [
  {
    // ppt/media/image35.png -- pin + roller both base-down, forces up and down.
    name: 'image35',
    geometry: {
      schemaVersion: 1,
      nodes: [
        { id: 1, x: 0, y: 0 },
        { id: 2, x: 1, y: 0 },
        { id: 3, x: 2, y: 0 },
        { id: 4, x: 1, y: 1 },
      ],
      members: [member(1, 1, 2), member(2, 1, 4), member(3, 2, 4), member(4, 2, 3), member(5, 3, 4)],
      supports: [
        { node: 1, type: 'pin', angleDeg: 0 },
        { node: 2, type: 'roller', angleDeg: 0 },
      ],
      forces: [
        { node: 4, fx: 0, fy: 5, label: '5F' },
        { node: 3, fx: 0, fy: -4, label: '4F' },
      ],
      bounds,
    },
  },
  {
    // ppt/media/image36.png -- the downward 3F must flip above its node.
    name: 'image36',
    geometry: {
      schemaVersion: 1,
      nodes: [
        { id: 1, x: -1, y: -1 },
        { id: 2, x: 0, y: 0 },
        { id: 3, x: 1, y: 0 },
        { id: 4, x: 1, y: -1 },
        { id: 5, x: 2, y: -1 },
      ],
      members: [
        member(1, 1, 2),
        member(2, 2, 4),
        member(3, 2, 3),
        member(4, 1, 4),
        member(5, 3, 4),
        member(6, 4, 5),
        member(7, 3, 5),
      ],
      supports: [
        { node: 1, type: 'pin', angleDeg: 0 },
        { node: 4, type: 'roller', angleDeg: 0 },
      ],
      forces: [
        { node: 2, fx: -1, fy: 0, label: 'F' },
        { node: 3, fx: 0, fy: -3, label: '3F' },
      ],
      bounds,
    },
  },
  {
    // ppt/media/image40.png -- rotated supports: pin above, roller to the right.
    name: 'image40',
    geometry: {
      schemaVersion: 1,
      nodes: [
        { id: 1, x: 0, y: 0 },
        { id: 2, x: 1, y: 0 },
        { id: 3, x: 0, y: -1 },
        { id: 4, x: 2, y: -1 },
      ],
      members: [member(1, 1, 3), member(2, 1, 2), member(3, 2, 3), member(4, 3, 4), member(5, 2, 4)],
      supports: [
        { node: 2, type: 'pin', angleDeg: 180 },
        { node: 4, type: 'roller', angleDeg: 90 },
      ],
      forces: [
        { node: 1, fx: 0, fy: 2, label: '2F' },
        { node: 3, fx: 1, fy: 0, label: 'F' },
      ],
      bounds,
    },
  },
]

/** Two sizes: the student workspace, and the 288px admin preview box. */
const SIZES = [
  { suffix: '', w: 1000, h: 640 },
  { suffix: '-preview', w: 576, h: 288 },
]

describe.skipIf(!OUT)('truss render samples', () => {
  it('writes HTML for each reference geometry', () => {
    const dir = OUT ?? ''
    mkdirSync(dir, { recursive: true })
    const samples = [...SAMPLES]
    if (EXTRA !== undefined && EXTRA !== '') {
      const extra = JSON.parse(readFileSync(EXTRA, 'utf-8')) as Record<string, Sample['geometry']>
      for (const [name, geometry] of Object.entries(extra)) samples.push({ name, geometry })
    }
    for (const s of samples) {
      const svg = renderToStaticMarkup(<TrussDiagram geometry={s.geometry} />)
      for (const size of SIZES) {
        const html = `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#fff}
.box{width:${String(size.w)}px;height:${String(size.h)}px}
svg{display:block;width:100%;height:100%}</style>
<div class="box">${svg}</div>`
        writeFileSync(join(dir, `${s.name}${size.suffix}.html`), html)
      }
    }
  })
})
