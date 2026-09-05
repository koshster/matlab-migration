import LoadArrow from './LoadArrow'
import MomentArc from './MomentArc'
import { PinSupport, RollerSupport, WallSupport } from './Supports'
import { collectPoints, num, parseGeometry, path, point, str, type Point } from './schema'

/**
 * Support and load glyphs are authored against roughly 4-unit geometry, the
 * same as truss. Unlike truss, nothing normalizes these coordinates on the
 * server -- the generic path forwards the generator's own units, which run
 * about 0..4 but are not guaranteed to -- so the fit happens here.
 */
const TARGET_SPAN = 4
const PAD = 1.8

const BODY_COLOR = '#1f2937'

interface Fit {
  scale: number
  bounds: { xMin: number; xMax: number; yMin: number; yMax: number }
}

function fitToView(points: Point[]): Fit {
  if (points.length === 0) {
    return { scale: 1, bounds: { xMin: -1, xMax: 1, yMin: -1, yMax: 1 } }
  }

  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys))
  // A degenerate body (single point, or a straight bar) has no span on one
  // axis; leave it at 1:1 rather than dividing by ~zero and exploding.
  const scale = span > 0.01 ? TARGET_SPAN / span : 1

  return {
    scale,
    bounds: {
      xMin: Math.min(...xs) * scale,
      xMax: Math.max(...xs) * scale,
      yMin: Math.min(...ys) * scale,
      yMax: Math.max(...ys) * scale,
    },
  }
}

export default function RigidBodyDiagram({ geometry }: { geometry: unknown }) {
  const elements = parseGeometry(geometry)
  const { scale, bounds } = fitToView(collectPoints(elements))

  const vbX = bounds.xMin - PAD
  const vbY = -(bounds.yMax + PAD)
  const vbW = bounds.xMax - bounds.xMin + PAD * 2
  const vbH = bounds.yMax - bounds.yMin + PAD * 2

  const fontSize = 0.3

  const bodyPaths = elements
    .filter((el) => el.element_type === 'rigid_body_path')
    .map((el) => path(el.properties.path))
    .filter((pts) => pts.length > 1)

  const supports = elements.filter((el) =>
    ['pin', 'roller', 'wall'].includes(el.element_type),
  )
  const loads = elements.filter((el) => el.element_type === 'point_load')
  const moments = elements.filter((el) => el.element_type === 'moment')
  const nodes = elements.filter((el) => el.element_type === 'node')

  if (elements.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
        This problem has no diagram to display.
      </div>
    )
  }

  return (
    <svg
      viewBox={`${String(vbX)} ${String(vbY)} ${String(vbW)} ${String(vbH)}`}
      className="h-full w-full"
      role="img"
      aria-labelledby="rigid-body-title rigid-body-desc"
    >
      <title id="rigid-body-title">Rigid body diagram</title>
      <desc id="rigid-body-desc">
        A rigid body in static equilibrium with {supports.length} support
        {supports.length === 1 ? '' : 's'}, {loads.length} applied load
        {loads.length === 1 ? '' : 's'} and {moments.length} applied moment
        {moments.length === 1 ? '' : 's'}.
      </desc>

      {/*
        Single y-flip. Physics coords are y-up, SVG is y-down; everything below
        is written in engineering coordinates and text counter-flips itself.
      */}
      <g transform="scale(1,-1)">
        {/* 1. The body itself (bottom layer). */}
        {bodyPaths.map((pts, i) => (
          <polyline
            key={i}
            points={pts.map((p) => `${String(p.x * scale)},${String(p.y * scale)}`).join(' ')}
            fill="none"
            stroke={BODY_COLOR}
            strokeWidth={0.14}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* 2. Supports. */}
        {supports.map((el, i) => {
          const at = point(el.properties.position)
          if (!at) return null
          const props = {
            x: at.x * scale,
            y: at.y * scale,
            rotation: num(el.properties.rotation),
            label: str(el.properties.label),
            fontSize,
          }
          if (el.element_type === 'pin') return <PinSupport key={i} {...props} />
          if (el.element_type === 'roller') return <RollerSupport key={i} {...props} />
          return <WallSupport key={i} {...props} />
        })}

        {/* 3. Applied loads and couples. */}
        {loads.map((el, i) => {
          const at = point(el.properties.position)
          const force = point(el.properties.force_vector)
          if (!at || !force) return null
          return (
            <LoadArrow
              key={i}
              x={at.x * scale}
              y={at.y * scale}
              fx={force.x}
              fy={force.y}
              label={str(el.properties.label)}
              fontSize={fontSize}
            />
          )
        })}

        {moments.map((el, i) => {
          const at = point(el.properties.position)
          if (!at) return null
          return (
            <MomentArc
              key={i}
              x={at.x * scale}
              y={at.y * scale}
              direction={num(el.properties.direction, 1)}
              arrowAngle={num(el.properties.arrow_angle)}
              arcAngle={num(el.properties.arc_angle, 200)}
              label={str(el.properties.label)}
              fontSize={fontSize}
            />
          )
        })}

        {/* 4. Joints on top, so the body path never hides one. */}
        {nodes.map((el, i) => (
          <circle
            key={i}
            cx={num(el.properties.x) * scale}
            cy={num(el.properties.y) * scale}
            r={0.11}
            fill={BODY_COLOR}
            stroke="#fff"
            strokeWidth={0.04}
          />
        ))}
      </g>
    </svg>
  )
}
