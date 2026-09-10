import { WallBar } from './SupportGlyph'

interface WallSupportProps {
  x: number
  y: number
  /** Generator convention: 0 = body runs down, 90 = body runs right, etc. */
  angleDeg: number
}

/**
 * The base angle a wall is actually drawn at.
 *
 * Unlike a pin or roller, the generator's wall rotation points *along* the
 * connected member instead of at the free side (`supports.py`: a member running
 * +x yields 90), so drawing it as given would put the bar through the body.
 * Adding 180 turns it into the same base-angle convention every other glyph
 * uses. Exported because the support letter has to be placed against the drawn
 * glyph, not the raw rotation.
 */
export function wallBaseAngle(angleDeg: number): number {
  return angleDeg + 180
}

/** Fixed (cantilever) wall support: a solid bar across the body's end. */
export default function WallSupport({ x, y, angleDeg }: WallSupportProps) {
  return <WallBar x={x} y={y} angleDeg={wallBaseAngle(angleDeg)} />
}
