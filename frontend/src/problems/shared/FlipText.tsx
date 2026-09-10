import type { ReactNode } from 'react'

interface FlipTextProps {
  /** Anchor point in physics coordinates (y-up). */
  x: number
  y: number
  fontSize: number
  fill: string
  anchor?: 'start' | 'middle' | 'end'
  baseline?: 'middle' | 'hanging' | 'auto'
  weight?: 'normal' | 'bold'
  children: ReactNode
}

/**
 * Text inside the diagram's single `scale(1,-1)` group. The inner flip cancels
 * the outer one so glyphs stay upright while the anchor stays in physics
 * coordinates.
 */
export default function FlipText({
  x,
  y,
  fontSize,
  fill,
  anchor = 'middle',
  baseline = 'middle',
  weight = 'normal',
  children,
}: FlipTextProps) {
  return (
    <g transform={`translate(${x},${y}) scale(1,-1)`}>
      <text
        x={0}
        y={0}
        fontSize={fontSize}
        fill={fill}
        textAnchor={anchor}
        dominantBaseline={baseline}
        fontFamily="Helvetica, Arial, sans-serif"
        fontWeight={weight}
      >
        {children}
      </text>
    </g>
  )
}
