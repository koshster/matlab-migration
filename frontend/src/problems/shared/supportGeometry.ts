/**
 * Unit vector from a support's node toward its base — the ground side.
 *
 * The glyph is authored base-down, so this is (0,-1) turned counter-clockwise
 * by `angleDeg`: 0 = below, 90 = right, 180 = above, 270 = left. That is the
 * convention `good_pin_support_orientation` enforces in the backend, which
 * accepts 90 only when nothing extends to +x — i.e. base to the right. (Note
 * that function's docstring describes the mirror image and is wrong; the code
 * is what both sides agree on, and `rigidBodyDiagram.test.tsx` pins it.)
 *
 * Lives apart from `SupportGlyph.tsx` so the label placer can use it without
 * a component module importing a module that imports it back.
 */
/** Math.cos(Math.PI * 1.5) is -1.8e-16, not 0; snap that noise away. */
const snap = (v: number): number => (Math.abs(v) < 1e-12 ? 0 : v)

export function baseDir(angleDeg: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180
  return { x: snap(Math.sin(rad)), y: snap(-Math.cos(rad)) }
}
