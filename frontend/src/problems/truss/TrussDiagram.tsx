import type { components } from '@statics/contract/src/index'
import Axes from './Axes'
import ForceArrow from './ForceArrow'
import Member from './Member'
import TrussNode from './Node'
import PinSupport from './PinSupport'
import RollerSupport from './RollerSupport'
import { MARGIN } from './constants'
import { placeMemberLabels } from './memberLabels'

type TrussGeometry = components['schemas']['TrussGeometry']
type TrussNodeT = components['schemas']['TrussNode']

/**
 * Direction cosine above which a member counts as "in the way" of a force.
 * MATLAB tests for a node in exactly that grid direction (drawForces.m:66-97),
 * so the threshold has to be tight enough that a 45-degree diagonal (0.707)
 * does not read as blocking.
 */
const BLOCKED_DOT = 0.9

interface Window {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

/**
 * plotTruss.m:135 (`focus`) — one unit of clearance past the extreme nodes,
 * snapped to the grid so the window edges land on gridlines.
 */
function plotWindow(nodes: TrussNodeT[]): Window {
  if (nodes.length === 0) return { xMin: -1, xMax: 1, yMin: -1, yMax: 1 }
  const xs = nodes.map((n) => n.x)
  const ys = nodes.map((n) => n.y)
  return {
    xMin: Math.floor(Math.min(...xs)) - 1,
    xMax: Math.ceil(Math.max(...xs)) + 1,
    yMin: Math.floor(Math.min(...ys)) - 1,
    yMax: Math.ceil(Math.max(...ys)) + 1,
  }
}

/** Unit directions of every member leaving each node, keyed by node id. */
function incidentDirections(g: TrussGeometry, nodeMap: Map<number, TrussNodeT>) {
  const out = new Map<number, Array<[number, number]>>()
  const push = (id: number, dir: [number, number]) => {
    const list = out.get(id)
    if (list) list.push(dir)
    else out.set(id, [dir])
  }
  for (const m of g.members) {
    const a = nodeMap.get(m.from)
    const b = nodeMap.get(m.to)
    if (!a || !b) continue
    const len = Math.hypot(b.x - a.x, b.y - a.y)
    if (len === 0) continue
    const ux = (b.x - a.x) / len
    const uy = (b.y - a.y) / len
    push(m.from, [ux, uy])
    push(m.to, [-ux, -uy])
  }
  return out
}

/**
 * drawForces.m:60-98 — shift the arrow to the far side of the node when the
 * force points into the structure and the opposite side is clear.
 */
function isShifted(dirs: Array<[number, number]>, ux: number, uy: number): boolean {
  const forwardBlocked = dirs.some(([mx, my]) => mx * ux + my * uy > BLOCKED_DOT)
  if (!forwardBlocked) return false
  const backwardBlocked = dirs.some(([mx, my]) => -(mx * ux + my * uy) > BLOCKED_DOT)
  return !backwardBlocked
}

export default function TrussDiagram({ geometry }: { geometry: unknown }) {
  const g = geometry as TrussGeometry

  const nodeMap = new Map(g.nodes.map((n) => [n.id, n]))
  const win = plotWindow(g.nodes)
  const dirs = incidentDirections(g, nodeMap)

  const drawable = g.members.flatMap((m) => {
    const from = nodeMap.get(m.from)
    const to = nodeMap.get(m.to)
    return from && to ? [{ id: m.id, from, to }] : []
  })
  const labels = placeMemberLabels(drawable, g.nodes)

  // The plot box plus room outside it for the tick labels. Physics y is up,
  // SVG y is down, hence the negated origin.
  const vbX = win.xMin - MARGIN.left
  const vbY = -(win.yMax + MARGIN.top)
  const vbW = win.xMax - win.xMin + MARGIN.left + MARGIN.right
  const vbH = win.yMax - win.yMin + MARGIN.top + MARGIN.bottom

  return (
    <svg
      viewBox={`${String(vbX)} ${String(vbY)} ${String(vbW)} ${String(vbH)}`}
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
          const shifted =
            mag > 0 && isShifted(dirs.get(f.node) ?? [], f.fx / mag, f.fy / mag)
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
