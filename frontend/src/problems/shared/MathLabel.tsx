import FlipText from './FlipText'

/**
 * Every quantity the diagrams annotate is a numeric multiple of a symbol:
 * `3F`, `2Fa`, `-2a`, `0`. The deck sets the multiplier upright and the symbol
 * italic, the way the source figures do (ppt/media/image4.png: "2Fa" has an
 * upright 2 and an italic Fa).
 *
 * Splitting on "leading sign and digits" rather than a hardcoded suffix is what
 * lets one component serve force labels, couple labels and axis ticks; the
 * previous per-call-site `splitLabel` only knew how to italicise a trailing F,
 * so a couple label like "4Fa" came out fully upright.
 */
export function splitQuantity(label: string): { head: string; symbol: string } {
  const match = /^([+-]?\d*\.?\d*)(.*)$/.exec(label)
  if (!match) return { head: label, symbol: '' }
  return { head: match[1], symbol: match[2] }
}

interface MathLabelProps {
  /** Anchor in physics coordinates (y-up); see FlipText. */
  x: number
  y: number
  /** e.g. "3F", "2Fa", "-2a", "0". */
  label: string
  fontSize: number
  fill: string
  anchor?: 'start' | 'middle' | 'end'
  baseline?: 'middle' | 'hanging' | 'auto'
  weight?: 'normal' | 'bold'
}

export default function MathLabel({ label, ...text }: MathLabelProps) {
  const { head, symbol } = splitQuantity(label)
  return (
    <FlipText {...text}>
      {head}
      {symbol === '' ? null : <tspan fontStyle="italic">{symbol}</tspan>}
    </FlipText>
  )
}
