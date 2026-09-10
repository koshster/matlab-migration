import { WallBar } from './SupportGlyph'

interface WallSupportProps {
  x: number
  y: number
  /** Generator convention: 0 = body runs right, 90 = body runs up, etc.
   *  drawnRotation adds 180 so the bar faces the opposite (ground) side. */
  angleDeg: number
}

/**
 * Fixed (cantilever) wall support. The generator's rotation points along the
 * body; the bar is drawn perpendicular on the ground side, so we add 180.
 */
export default function WallSupport({ x, y, angleDeg }: WallSupportProps) {
  const barAngle = angleDeg + 180
  return <WallBar x={x} y={y} angleDeg={barAngle} />
}
