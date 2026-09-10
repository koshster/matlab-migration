import { useId } from 'react'
import Axes from '../shared/Axes'
import BodyPipes from '../shared/BodyPipes'
import ForceArrow from '../shared/ForceArrow'
import PinSupport from '../shared/PinSupport'
import RollerSupport from '../shared/RollerSupport'
import WallSupport, { wallBaseAngle } from '../shared/WallSupport'
import { buildShiftRule, pathSegments } from '../shared/forceShift'
import { plotWindow, viewBox } from '../shared/plotWindow'
import { SupportLabel } from '../shared/SupportGlyph'
import MomentArc from './MomentArc'
import { collectPoints, num, parseGeometry, path, point, str } from './schema'

const SUPPORT_TYPES = ['pin', 'roller', 'wall'] as const
type SupportType = (typeof SUPPORT_TYPES)[number]

const isSupport = (type: string): type is SupportType =>
  (SUPPORT_TYPES as readonly string[]).includes(type)

export default function RigidBodyDiagram({ geometry }: { geometry: unknown }) {
  const uid = useId()
  const titleId = `rb-title-${uid}`
  const descId = `rb-desc-${uid}`

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

  const supports = elements.filter((el) => isSupport(el.element_type))
  const loads = elements.filter((el) => el.element_type === 'point_load')
  const moments = elements.filter((el) => el.element_type === 'moment')

  const win = plotWindow(collectPoints(elements))
  const segments = pathSegments(bodyPaths)
  const shouldShift = buildShiftRule(segments)

  return (
    <svg
      viewBox={viewBox(win)}
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

      {/*
        Single y-flip group. Physics coords are y-up; SVG is y-down.
        Everything rendered inside this group uses engineering coordinates
        directly. Text labels counter-flip themselves internally.
      */}
      <g transform="scale(1,-1)">
        <Axes xMin={win.xMin} xMax={win.xMax} yMin={win.yMin} yMax={win.yMax} />

        <BodyPipes paths={bodyPaths} />

        {/* Supports and loads sit on top of the body so they stay readable
            wherever they land -- see OPACITY in constants.ts. */}
        {supports.map((el, i) => {
          const at = point(el.properties.position)
          if (!at) return null
          const rotation = num(el.properties.rotation)
          const kind = el.element_type as SupportType

          // A wall's rotation points along the body rather than at the free
          // side, so its drawn base angle is the flipped one -- and the letter
          // has to follow the glyph, not the raw rotation.
          const drawnAngle = kind === 'wall' ? wallBaseAngle(rotation) : rotation

          return (
            <g key={i}>
              {kind === 'pin' && <PinSupport x={at.x} y={at.y} angleDeg={rotation} />}
              {kind === 'roller' && <RollerSupport x={at.x} y={at.y} angleDeg={rotation} />}
              {kind === 'wall' && <WallSupport x={at.x} y={at.y} angleDeg={rotation} />}
              <SupportLabel
                x={at.x}
                y={at.y}
                angleDeg={drawnAngle}
                label={str(el.properties.label)}
                segments={segments}
              />
            </g>
          )
        })}

        {loads.map((el, i) => {
          const at = point(el.properties.position)
          const force = point(el.properties.force_vector)
          if (!at || !force) return null
          const mag = Math.hypot(force.x, force.y)
          if (mag === 0) return null
          return (
            <ForceArrow
              key={i}
              node={at}
              fx={force.x}
              fy={force.y}
              label={str(el.properties.label)}
              shifted={shouldShift(at, force.x / mag, force.y / mag)}
            />
          )
        })}

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
