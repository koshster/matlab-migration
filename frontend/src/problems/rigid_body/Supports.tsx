import FlipText from './FlipText'
import Hatching from './Hatching'

type SupportKind = 'pin' | 'roller' | 'wall'

interface SupportProps {
  x: number
  y: number
  /** Generator's orientation code; see `drawnRotation` for what it means. */
  rotation: number
  label: string
  fontSize: number
}

// Apex at the anchor, base below it, in physics coords (y-up).
const TRIANGLE = '0,0 -0.45,-0.65 0.45,-0.65'
const GROUND_Y = -0.72
const HALF_WIDTH = 0.55
const LABEL_DISTANCE = 1.15

/**
 * Turn the generator's orientation code into the angle the glyph is rotated by.
 *
 * For pins and rollers the code names the side the base sits on, measured so
 * that 0 is below, 90 right, 180 above, 270 left. That is the convention
 * `good_pin_support_orientation` enforces -- rotation 90 is accepted only when
 * nothing extends to +x -- and it is the one to trust. (The docstring beside
 * that guard says 90 means "left"; drawing it that way puts the support base
 * through the body on about a third of generated problems, so the prose is
 * what is wrong, not the guard.)
 *
 * A wall is the other way round: its code points along the body, because a
 * cantilever sticks straight out of its wall. The face is already
 * perpendicular either way, so only the hatching needs flipping to land on the
 * outside.
 */
function drawnRotation(kind: SupportKind, rotation: number): number {
  return kind === 'wall' ? rotation + 180 : rotation
}

const toRad = (deg: number): number => (deg * Math.PI) / 180

/**
 * Unit vector the base points along after `drawnRotation`, i.e. `(0,-1)` turned
 * counter-clockwise by that angle.
 */
function baseDirection(angle: number): { x: number; y: number } {
  return { x: Math.sin(toRad(angle)), y: -Math.cos(toRad(angle)) }
}

interface SupportGlyphProps extends SupportProps {
  kind: SupportKind
}

/**
 * Shared frame: rotated glyph, plus an upright label.
 *
 * The label sits past the hatching on the base side, which the generator
 * guarantees is clear of the body, and is deliberately left out of the rotated
 * group -- turned on its side it would be unreadable, and this label is the
 * only thing tying the picture to the `reaction_Ax` answer fields.
 */
function SupportGlyph({ kind, x, y, rotation, label, fontSize }: SupportGlyphProps) {
  const angle = drawnRotation(kind, rotation)
  const direction = baseDirection(angle)

  return (
    <g>
      <g transform={`translate(${String(x)},${String(y)}) rotate(${String(angle)})`}>
        {kind === 'pin' && (
          <polygon points={TRIANGLE} fill="#9ca3af" stroke="#6b7280" strokeWidth={0.05} />
        )}
        {kind === 'roller' && (
          <>
            <polygon points={TRIANGLE} fill="#d1d5db" stroke="#6b7280" strokeWidth={0.05} />
            {/* Wheel at the triangle centroid, the tell that this one can slide. */}
            <circle cx={0} cy={-0.43} r={0.16} fill="#fff" stroke="#6b7280" strokeWidth={0.05} />
          </>
        )}
        {/* A wall is built into the ground, so its face passes through the
            anchor rather than sitting below a triangle. */}
        <Hatching
          halfWidth={kind === 'wall' ? 0.9 : HALF_WIDTH}
          y={kind === 'wall' ? 0 : GROUND_Y}
        />
      </g>
      {label && (
        <FlipText
          x={x + direction.x * LABEL_DISTANCE}
          y={y + direction.y * LABEL_DISTANCE}
          fontSize={fontSize}
          fill="#374151"
          plate
        >
          {label}
        </FlipText>
      )}
    </g>
  )
}

export function PinSupport(props: SupportProps) {
  return <SupportGlyph kind="pin" {...props} />
}

export function RollerSupport(props: SupportProps) {
  return <SupportGlyph kind="roller" {...props} />
}

export function WallSupport(props: SupportProps) {
  return <SupportGlyph kind="wall" {...props} />
}
