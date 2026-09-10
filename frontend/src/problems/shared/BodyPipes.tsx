import { COLORS, GEOM } from './constants'

interface BodyPipesProps {
  /** One polyline per run of the body; a body may be several crossing runs. */
  paths: Array<Array<{ x: number; y: number }>>
}

/**
 * A non-deformable body drawn as a run of pipe, matching the truss member
 * treatment: lavender fill, hairline dark outline, rounded joins and caps
 * (ppt/media/image4.png, image34.png).
 *
 * Every outline is stroked before any fill, rather than outlining and filling
 * one path at a time. Bodies are frequently several crossing runs — the "+"
 * body in ppt/media/image2.png is two — and per-path ordering leaves the
 * second run's outline drawn across the first run's face. Stroking all the
 * outlines first means the fills cover every edge interior to the union, so
 * the outline survives only on the true silhouette, which is what the deck
 * shows.
 */
export default function BodyPipes({ paths }: BodyPipesProps) {
  const runs = paths.filter((pts) => pts.length > 1)
  const pointsOf = (pts: Array<{ x: number; y: number }>) =>
    pts.map((p) => `${String(p.x)},${String(p.y)}`).join(' ')

  const width = GEOM.bodyHalfWidth * 2

  return (
    <g>
      {runs.map((pts, i) => (
        <polyline
          key={`edge${String(i)}`}
          points={pointsOf(pts)}
          fill="none"
          stroke={COLORS.outline}
          strokeWidth={width + GEOM.outlineWidth * 2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}
      {runs.map((pts, i) => (
        <polyline
          key={`face${String(i)}`}
          points={pointsOf(pts)}
          fill="none"
          stroke={COLORS.member}
          strokeWidth={width}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}
    </g>
  )
}
