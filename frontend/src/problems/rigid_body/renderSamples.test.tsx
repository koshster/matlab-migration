import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, it } from 'vitest'
import RigidBodyDiagram from './RigidBodyDiagram'
import { fixtures } from './fixtures'

/**
 * Dev-only harness, the rigid-body twin of `truss/renderSamples.test.tsx`:
 * writes standalone HTML for each captured generator fixture plus the
 * geometries transcribed from the reference slides in `docs/Images.pptx`, so a
 * render can be screenshotted and compared side by side with the originals.
 * Skipped unless RB_RENDER_OUT is set, so it is inert in CI.
 *
 *   RB_RENDER_OUT=/tmp/rb node_modules/.bin/vitest run src/problems/rigid_body/renderSamples.test.tsx
 */
const OUT = process.env.RB_RENDER_OUT
/** Optional JSON file of `{ name: RigidBodyGeometry }` — e.g. real generator output. */
const EXTRA = process.env.RB_RENDER_EXTRA

const bodyPath = (...pts: Array<[number, number]>) => ({
  element_type: 'rigid_body_path',
  properties: { path: pts },
})

/**
 * Hand-transcribed from the deck so the styling can be checked against the
 * exact figures it is meant to reproduce, not just against generator output.
 */
const SLIDE_SAMPLES: Record<string, unknown> = {
  // ppt/media/image6.png — the "C"-with-a-tail body, roller above B, roller
  // below A, F down at mid-span and 2F right off the tail.
  image6: {
    schemaVersion: 1,
    elements: [
      bodyPath([0, 0], [-1, 0], [-1, -2], [1, -2]),
      bodyPath([-1, -1], [1, -1]),
      bodyPath([0, -2], [0, -3]),
      { element_type: 'roller', properties: { position: [0, 0], rotation: 0, label: 'B' } },
      { element_type: 'roller', properties: { position: [1, -1], rotation: 180, label: 'A' } },
      {
        element_type: 'point_load',
        properties: { position: [0, -2], force_vector: [0, -1], label: 'F' },
      },
      {
        element_type: 'point_load',
        properties: { position: [0, -3], force_vector: [2, 0], label: '2F' },
      },
    ],
  },
  // ppt/media/image33.png — cantilever: staple-shaped body on a fixed wall at A.
  image33: {
    schemaVersion: 1,
    elements: [
      bodyPath([0, 1], [0, 0], [3, 0], [3, -1]),
      { element_type: 'wall', properties: { position: [3, -1], rotation: 180, label: 'A' } },
      {
        element_type: 'point_load',
        properties: { position: [0, 0], force_vector: [0, 3], label: '3F' },
      },
      {
        element_type: 'point_load',
        properties: { position: [3, 0], force_vector: [0, -1], label: 'F' },
      },
    ],
  },
  // ppt/media/image34.png — three rollers (A left-facing, B above, C left-facing)
  // plus a CCW couple 4Fa at the elbow.
  image34: {
    schemaVersion: 1,
    elements: [
      bodyPath([0, 0], [1, 0], [1, 1], [2, 1], [2, 0]),
      { element_type: 'roller', properties: { position: [1, 1], rotation: 270, label: 'A' } },
      { element_type: 'roller', properties: { position: [2, 1], rotation: 180, label: 'B' } },
      { element_type: 'roller', properties: { position: [2, 0], rotation: 270, label: 'C' } },
      {
        element_type: 'point_load',
        properties: { position: [0, 0], force_vector: [1, 0], label: 'F' },
      },
      {
        element_type: 'moment',
        properties: { position: [1, 0], direction: 1, arrow_angle: 135, arc_angle: 240, label: '4Fa' },
      },
    ],
  },
}

/** Two sizes: the student workspace, and the 288px admin preview box. */
const SIZES = [
  { suffix: '', w: 1000, h: 640 },
  { suffix: '-preview', w: 576, h: 288 },
]

describe.skipIf(!OUT)('rigid body render samples', () => {
  it('writes HTML for each reference geometry', () => {
    const dir = OUT ?? ''
    mkdirSync(dir, { recursive: true })

    const samples: Record<string, unknown> = { ...fixtures, ...SLIDE_SAMPLES }
    if (EXTRA !== undefined && EXTRA !== '') {
      Object.assign(samples, JSON.parse(readFileSync(EXTRA, 'utf-8')) as Record<string, unknown>)
    }

    for (const [name, geometry] of Object.entries(samples)) {
      const svg = renderToStaticMarkup(<RigidBodyDiagram geometry={geometry} />)
      for (const size of SIZES) {
        const html = `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#fff}
.box{width:${String(size.w)}px;height:${String(size.h)}px}
svg{display:block;width:100%;height:100%}</style>
<div class="box">${svg}</div>`
        writeFileSync(join(dir, `${name}${size.suffix}.html`), html)
      }
    }
  })
})
