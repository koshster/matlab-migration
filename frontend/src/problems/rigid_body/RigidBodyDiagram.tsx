import { useId } from 'react'
import Axes from '../shared/Axes'
import { COLORS, GEOM, MARGIN } from '../shared/constants'
import FlipText from '../shared/FlipText'
import ForceArrow from '../shared/ForceArrow'
import PinSupport from '../shared/PinSupport'
import { plotWindow } from '../shared/plotWindow'
import RollerSupport from '../shared/RollerSupport'
import WallSupport from '../shared/WallSupport'
import MomentArc from './MomentArc'
import { collectPoints, num, parseGeometry, path, point, str } from './schema'

const BLOCKED_DOT = 0.9
const LABEL_DISTANCE = 1.15

const toRad = (deg: number): number => (deg * Math.PI) / 180

/** Unit vector pointing toward the ground side of a support (base direction). */
function baseDir(angleDeg: number): { x: number; y: number } {
  return { x: Math.sin(toRad(angleDeg)), y: -Math.cos(toRad(angleDeg)) }
}

/**
 * Build incident direction map from rigid body path segments.
 * Key: "x,y" string of a vertex; value: unit vectors of segments leaving it.
 */
function incidentDirsFromPaths(
  paths: Array<Array<[number, number]>>,
): Map<string, Array<[number, number]>> {
  const out = new Map<string, Array<[number, number]>>()
  const push = (key: string, dir: [number, number]) => {
    const list = out.get(key)
    if (list) list.push(dir)
    else out.set(key, [dir])
  }
  for (const pts of paths) {
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i]
      const [bx, by] = pts[i + 1]
      const len = Math.hypot(bx - ax, by - ay)
      if (len < 1e-9) continue
      const ux = (bx - ax) / len
      const uy = (by - ay) / len
      push(`${String(ax)},${String(ay)}`, [ux, uy])
      push(`${String(bx)},${String(by)}`, [-ux, -uy])
    }
  }
  return out
}

/** drawForces.m:60-98 — shift when force direction is blocked by structure. */
function isShifted(dirs: Array<[number, number]>, ux: number, uy: number): boolean {
  const forwardBlocked = dirs.some(([mx, my]) => mx * ux + my * uy > BLOCKED_DOT)
  if (!forwardBlocked) return false
  const backwardBlocked = dirs.some(([mx, my]) => -(mx * ux + my * uy) > BLOCKED_DOT)
  return !backwardBlocked
}

export default function RigidBodyDiagram({ geometry }: { geometry: unknown }) {
  const titleId = `rb-title-${useId()}`
  const descId = `rb-desc-${useId()}`

  const elements = parseGeometry(geometry)
  if (elements.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
        This problem has no diagram to display.
      </div>
    )
  }

  const bodyPaths = elements
    .filter((el) => el.element_type === 'rigid_body_path')
    .map((el) => path(el.properties.path))
    .filter((pts) => pts.length > 1)

  const supports = elements.filter((el) => ['pin', 'roller', 'wall'].includes(el.element_type))
  const loads = elements.filter((el) => el.element_type === 'point_load')
  const moments = elements.filter((el) => el.element_type === 'moment')

  const win = plotWindow(collectPoints(elements))

  // Raw path vertex arrays for shift-rule computation.
  const rawPaths = bodyPaths.map((pts) => pts.map((p): [number, number] => [p.x, p.y]))
  const incidentDirs = incidentDirsFromPaths(rawPaths)

  const vbX = win.xMin - MARGIN.left
  const vbY = -(win.yMax + MARGIN.top)
  const vbW = win.xMax - win.xMin + MARGIN.left + MARGIN.right
  const vbH = win.yMax - win.yMin + MARGIN.top + MARGIN.bottom

  const memberHW = GEOM.memberHalfWidth * 2.5
  const outW = GEOM.outlineWidth * 6

  return (
    <svg
      viewBox={`${String(vbX)} ${String(vbY)} ${String(vbW)} ${String(vbH)}`}
      className="h-full w-full"
      role="img"
      aria-labelledby={`${titleId} ${descId}`}
    >
      <title id={titleId}>Rigid body diagram</title>
      <desc id={descId}>
        A rigid body in static equilibrium with {supports.length} support
        {supports.length === 1 ? '' : 's'}, {loads.length} applied load
        {loads.length === 1 ? '' : 's'} and {moments.length} applied moment
        {moments.length === 1 ? '' : 's'}.
      </desc>

      <g transform="scale(1,-1)">
        <Axes xMin={win.xMin} xMax={win.xMax} yMin={win.yMin} yMax={win.yMax} />

        {/* Body: dark outline pass then lavender fill pass, both with round caps. */}
        {bodyPaths.map((pts, i) => {
          const ptStr = pts.map((p) => `${String(p.x)},${String(p.y)}`).join(' ')
          return (
            <g key={i}>
              <polyline
                points={ptStr}
                fill="none"
                stroke={COLORS.outline}
                strokeWidth={memberHW * 2 + outW * 2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <polyline
                points={ptStr}
                fill="none"
                stroke={COLORS.member}
                strokeWidth={memberHW * 2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </g>
          )
        })}

        {/* Supports — shared glyphs already carry OPACITY.support via SupportFrame. */}
        {supports.map((el, i) => {
          const at = point(el.properties.position)
          if (!at) return null
          const rotation = num(el.properties.rotation)
          const label = str(el.properties.label)
          const kind = el.element_type as 'pin' | 'roller' | 'wall'

          // Label base direction: wall uses rotation+180 (body points along rotation,
          // wall face is the opposite side); pin/roller use rotation directly.
          const labelAngle = kind === 'wall' ? rotation + 180 : rotation
          const dir = baseDir(labelAngle)

          return (
            <g key={i}>
              {kind === 'pin' && <PinSupport x={at.x} y={at.y} angleDeg={rotation} />}
              {kind === 'roller' && <RollerSupport x={at.x} y={at.y} angleDeg={rotation} />}
              {kind === 'wall' && <WallSupport x={at.x} y={at.y} angleDeg={rotation} />}
              {label !== '' && (
                <FlipText
                  x={at.x + dir.x * LABEL_DISTANCE}
                  y={at.y + dir.y * LABEL_DISTANCE}
                  fontSize={0.2}
                  fill={COLORS.outline}
                  anchor="middle"
                >
                  {label}
                </FlipText>
              )}
            </g>
          )
        })}

        {/* Applied loads — shared 7-gon ForceArrow with shift rule. */}
        {loads.map((el, i) => {
          const at = point(el.properties.position)
          const force = point(el.properties.force_vector)
          if (!at || !force) return null
          const mag = Math.hypot(force.x, force.y)
          if (mag === 0) return null
          const ux = force.x / mag
          const uy = force.y / mag
          const key = `${String(at.x)},${String(at.y)}`
          const dirs = incidentDirs.get(key) ?? []
          const shifted = isShifted(dirs, ux, uy)
          return (
            <ForceArrow
              key={i}
              node={at}
              fx={force.x}
              fy={force.y}
              label={str(el.properties.label)}
              shifted={shifted}
            />
          )
        })}

        {/* Moments — arc with filled arrowhead, no <marker>. */}
        {moments.map((el, i) => {
          const at = point(el.properties.position)
          if (!at) return null
          return (
            <MomentArc
              key={i}
              x={at.x}
              y={at.y}
              direction={num(el.properties.direction, 1)}
              arrowAngle={num(el.properties.arrow_angle)}
              arcAngle={num(el.properties.arc_angle, 200)}
              label={str(el.properties.label)}
            />
          )
        })}
      </g>
    </svg>
  )
}
