import { useId } from 'react'
import FlipText from './FlipText'

interface LoadArrowProps {
  x: number
  y: number
  fx: number
  fy: number
  label: string
  fontSize: number
}

const LENGTH = 1.3
const COLOR = '#dc2626'

/**
 * Applied point load: tail out in space, tip on the body, so the arrow reads as
 * pushing into the point it acts on.
 */
export default function LoadArrow({ x, y, fx, fy, label, fontSize }: LoadArrowProps) {
  // useId, not a module counter: two diagrams on one page (review mode renders
  // several) would otherwise race for the same marker id and share arrowheads.
  const markerId = `rb-arrowhead-${useId()}`

  const magnitude = Math.hypot(fx, fy)
  if (magnitude === 0) return null

  const ux = fx / magnitude
  const uy = fy / magnitude

  const tailX = x - ux * LENGTH
  const tailY = y - uy * LENGTH

  // Three-quarters back toward the tail, nudged off-axis, so the label clears
  // both the body and the arrow itself.
  const offset = fontSize * 1.2
  const labelX = x + (tailX - x) * 0.75 - uy * offset
  const labelY = y + (tailY - y) * 0.75 + ux * offset

  return (
    <g>
      <defs>
        <marker id={markerId} markerWidth={6} markerHeight={6} refX={5} refY={3} orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill={COLOR} />
        </marker>
      </defs>
      <line
        x1={tailX}
        y1={tailY}
        x2={x}
        y2={y}
        stroke={COLOR}
        strokeWidth={0.1}
        markerEnd={`url(#${markerId})`}
      />
      {label && (
        <FlipText x={labelX} y={labelY} fontSize={fontSize} fill={COLOR} plate>
          {label}
        </FlipText>
      )}
    </g>
  )
}
