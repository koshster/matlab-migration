import type { components } from '@statics/contract/src/index'
import Member from './Member'
import TrussNode from './Node'
import PinSupport from './PinSupport'
import RollerSupport from './RollerSupport'
import ForceArrow from './ForceArrow'

type TrussGeometry = components['schemas']['TrussGeometry']

const PAD = 1.5

export default function TrussDiagram({ geometry }: { geometry: unknown }) {
  const g = geometry as TrussGeometry

  const vbX = g.bounds.xMin - PAD
  const vbY = -(g.bounds.yMax + PAD)
  const vbW = g.bounds.xMax - g.bounds.xMin + PAD * 2
  const vbH = g.bounds.yMax - g.bounds.yMin + PAD * 2

  // Build node lookup for member rendering
  const nodeMap = new Map(g.nodes.map((n) => [n.id, n]))

  // Truss centroid — used to pick outward perpendicular direction for each label
  const nodeCount = g.nodes.length || 1
  const centroid = {
    x: g.nodes.reduce((s, n) => s + n.x, 0) / nodeCount,
    y: g.nodes.reduce((s, n) => s + n.y, 0) / nodeCount,
  }

  // Derive label size from shortest member so labels scale with diagram density
  const memberLengths = g.members.map((m) => {
    const a = nodeMap.get(m.from)
    const b = nodeMap.get(m.to)
    if (!a || !b) return Infinity
    return Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
  })
  const minLen = Math.min(...memberLengths, Infinity)
  const labelSize = Math.min(Math.max(minLen * 0.14, 0.24), 0.32)
  const labelOffset = labelSize * 1.2

  return (
    <svg
      viewBox={`${vbX} ${vbY} ${vbW} ${vbH}`}
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
      <g transform={`scale(1,-1)`}>

        {/* 1. Members (bottom layer) */}
        {g.members.map((m) => {
          const from = nodeMap.get(m.from)
          const to = nodeMap.get(m.to)
          if (!from || !to) return null
          return <Member key={m.id} from={from} to={to} label={m.label} fontSize={labelSize} offset={labelOffset} centroid={centroid} />
        })}

        {/* 2. Supports */}
        {g.supports.map((s, i) => {
          const node = nodeMap.get(s.node)
          if (!node) return null
          return s.type === 'pin'
            ? <PinSupport key={i} x={node.x} y={node.y} angleDeg={s.angleDeg} />
            : <RollerSupport key={i} x={node.x} y={node.y} angleDeg={s.angleDeg} />
        })}

        {/* 3. Force arrows */}
        {g.forces.map((f, i) => {
          const node = nodeMap.get(f.node)
          if (!node) return null
          return <ForceArrow key={i} node={node} fx={f.fx} fy={f.fy} label={f.label} fontSize={labelSize} />
        })}

        {/* 4. Nodes (top layer — drawn last so they're never hidden by members) */}
        {g.nodes.map((n) => (
          <TrussNode key={n.id} x={n.x} y={n.y} />
        ))}

      </g>
    </svg>
  )
}
