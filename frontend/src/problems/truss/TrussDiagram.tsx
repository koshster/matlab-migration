import type { components } from '@statics/contract/src/index'
import Axes from '../shared/Axes'
import ForceArrow from '../shared/ForceArrow'
import PinSupport from '../shared/PinSupport'
import RollerSupport from '../shared/RollerSupport'
import { buildShiftRule } from '../shared/forceShift'
import { plotWindow, viewBox } from '../shared/plotWindow'
import Member from './Member'
import TrussNode from './Node'
import { placeMemberLabels } from './memberLabels'

type TrussGeometry = components['schemas']['TrussGeometry']

export default function TrussDiagram({ geometry }: { geometry: unknown }) {
  const g = geometry as TrussGeometry

  const nodeMap = new Map(g.nodes.map((n) => [n.id, n]))
  const win = plotWindow(g.nodes)

  const drawable = g.members.flatMap((m) => {
    const from = nodeMap.get(m.from)
    const to = nodeMap.get(m.to)
    return from && to ? [{ id: m.id, from, to }] : []
  })
  const labels = placeMemberLabels(drawable, g.nodes)
  const shouldShift = buildShiftRule(drawable)

  return (
    <svg
      viewBox={viewBox(win)}
      className="h-full w-full"
      role="img"
      aria-labelledby="truss-title truss-desc"
    >
      <title id="truss-title">Truss diagram</title>
      <desc id="truss-desc">
        A planar truss with {g.nodes.length} nodes and {g.members.length} members.
      </desc>

      {/*
        Single y-flip group. Physics coords are y-up; SVG is y-down.
        Everything rendered inside this group uses engineering coordinates directly.
        Text labels counter-flip themselves internally.
      */}
      <g transform="scale(1,-1)">
        <Axes xMin={win.xMin} xMax={win.xMax} yMin={win.yMin} yMax={win.yMax} />

        {drawable.map((m) => {
          const label = labels.get(m.id)
          if (!label) return null
          return <Member key={m.id} from={m.from} to={m.to} number={m.id} label={label} />
        })}

        {/* Structure first, back to front: members, then the joint caps that
            close their outlines. */}
        {g.nodes.map((n) => (
          <TrussNode key={n.id} x={n.x} y={n.y} />
        ))}

        {/* Supports and forces sit on top of the structure so they stay readable
            wherever they land -- see OPACITY in constants.ts. */}
        {g.supports.map((s, i) => {
          const node = nodeMap.get(s.node)
          if (!node) return null
          return s.type === 'pin' ? (
            <PinSupport key={i} x={node.x} y={node.y} angleDeg={s.angleDeg} />
          ) : (
            <RollerSupport key={i} x={node.x} y={node.y} angleDeg={s.angleDeg} />
          )
        })}

        {g.forces.map((f, i) => {
          const node = nodeMap.get(f.node)
          if (!node) return null
          const mag = Math.hypot(f.fx, f.fy)
          const shifted = mag > 0 && shouldShift(node, f.fx / mag, f.fy / mag)
          return (
            <ForceArrow
              key={i}
              node={node}
              fx={f.fx}
              fy={f.fy}
              label={f.label}
              shifted={shifted}
            />
          )
        })}
      </g>
    </svg>
  )
}
