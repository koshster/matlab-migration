interface FlipTextProps {
  x: number
  y: number
  fontSize: number
  fill: string
  children: string
  /** Draw a translucent plate behind the text so it stays legible over geometry. */
  plate?: boolean
}

/**
 * A label placed in physics coords (y-up) that still reads right way up.
 *
 * The diagram flips the whole scene with `scale(1,-1)`; text has to undo that
 * or it renders mirrored. Counter-flipping in place needs the `translate(0,
 * -2y)` so the glyph lands back on the point it was anchored to.
 */
export default function FlipText({ x, y, fontSize, fill, children, plate = false }: FlipTextProps) {
  const plateW = children.length * fontSize * 0.65
  const plateH = fontSize * 1.5

  return (
    <g transform={`scale(1,-1) translate(0,${String(-2 * y)})`}>
      {plate && (
        <rect
          x={x - plateW / 2}
          y={y - plateH / 2}
          width={plateW}
          height={plateH}
          rx={plateH / 4}
          fill="white"
          fillOpacity={0.85}
        />
      )}
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={fontSize}
        fill={fill}
        fontFamily="sans-serif"
        fontWeight="700"
      >
        {children}
      </text>
    </g>
  )
}
