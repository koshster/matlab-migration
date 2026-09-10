/**
 * Drawing constants ported from the MATLAB reference renderer
 * (`assets/Truss v5.4/+figPkg/`), which produced the diagrams in
 * `docs/Images.pptx`. Every length is in units of `a` — one grid square, which
 * is also one wire coordinate unit, because the backend keeps truss nodes on
 * the generator's integer grid.
 *
 * Where a value deviates from MATLAB it is marked DEVIATION with the reason.
 * The MATLAB figures are ~1500px wide; ours render as small as 288px, so type
 * and hairlines have to be proportionally larger to stay legible.
 */

/** Colours sampled from the presentation renders (ppt/media/image35|36|40.png). */
export const COLORS = {
  member: '#ADADC7',
  outline: '#111111',
  nodeDot: '#808080',
  memberLabel: '#000080',
  force: '#8B0000',
  pinFill: '#F3C3A6',
  rollerFill: '#DFBAF4',
  wheelFill: '#BBE1B7',
  ground: '#55553D',
  grid: '#DEDEDE',
  axis: '#333333',
  axisLight: '#BBBBBB',
  tick: '#262626',
} as const

export const GEOM = {
  /** plotTruss.m:11 `pipe_radius` — half-width of a member. */
  memberHalfWidth: 0.05,
  /** plotTruss.m:13 `edge_width` = 1pt, expressed in data units. */
  outlineWidth: 0.009,

  /** plotTruss.m:43 round pipe cap; doubles as the visible joint ring. */
  nodeCapRadius: 0.05,
  /** plotTruss.m:74 `MarkerSize` 5pt. */
  nodeDotRadius: 0.022,

  /**
   * drawSupports.m:83-88. Equilateral triangle, side 0.3, apex `nudge`=0.025
   * above the node so it tucks under the joint.
   */
  triangleApexY: 0.025,
  triangleBaseY: -0.2348076,
  triangleHalfBase: 0.15,

  /** drawSupports.m:71 `heightOfSupport` = 0.89*sqrt(3)/2*0.3. */
  supportHeight: 0.2312288,

  /** drawSupports.m:103-108 — one 30-gon wheel, tangent to the triangle base. */
  wheelCenterY: -0.2848076,
  wheelRadius: 0.05,

  /** drawSupports.m:120-127 — the pin's ground bar is the wider of the two. */
  pinBarY: -0.2312288,
  pinBarHalfLength: 0.3,
  /** drawSupports.m:110-115 — the roller's bar sits below the wheel and is shorter. */
  rollerBarY: -0.3312288,
  rollerBarHalfLength: 0.2312288,
  /** DEVIATION: 0.01 in drawSupports.m:73; nudged so it survives a 288px render. */
  barThickness: 0.014,

  /** drawForces.m:3 `lenF` — constant, independent of magnitude. */
  arrowLength: 0.5,
  /** drawArrow.m:22-25, normalised by arrow length. */
  arrowHeadHalfWidth: 0.08,
  /** DEVIATION: `W2` is 0.014 in drawArrow.m:23; widened so the shaft holds up small. */
  arrowShaftHalfWidth: 0.02,
  arrowHeadLength: 0.18,
  arrowInsetLength: 0.13,

  /** DEVIATION: 0.11 in plotTruss.m:47; opened up to clear the larger type. */
  memberLabelOffset: 0.14,
  /** drawForces.m:15 — label sits 0.1 past the tip, or 0.15 past the tail when shifted. */
  forceLabelUnshifted: 1.2,
  forceLabelShifted: -1.3,
} as const

/**
 * Supports and force arrows draw on top of the members so they always read
 * clearly, but at slightly less than full opacity so a member running under a
 * support triangle or an arrow shaft still shows through instead of vanishing.
 * 0.85 is the point where the overlap is legible without the glyphs looking
 * washed out.
 */
export const OPACITY = {
  support: 0.85,
  force: 0.85,
} as const

/**
 * Font sizes in units of `a`. DEVIATION: ~2x the MATLAB point sizes (12pt member,
 * 18pt force, 10pt tick) relative to the figure, because our canvas is smaller.
 * The 12:18:10 ratio between them is preserved.
 */
export const TYPE = {
  memberLabel: 0.13,
  forceLabel: 0.2,
  tickLabel: 0.15,
} as const

/** Room outside the plot box for the tick labels, in units of `a`. */
export const MARGIN = {
  left: 0.62,
  right: 0.16,
  top: 0.16,
  bottom: 0.5,
} as const

/**
 * drawArrow.m:30-32 — the arrow is one filled 7-gon, not a line plus a marker.
 * Points are normalised: tail at (0,0), tip at (1,0).
 */
export function arrowPolygon(length: number): Array<[number, number]> {
  const { arrowHeadHalfWidth: w1, arrowShaftHalfWidth: w2 } = GEOM
  const { arrowHeadLength: l1, arrowInsetLength: l2 } = GEOM
  const pts: Array<[number, number]> = [
    [0, w2],
    [1 - l2, w2],
    [1 - l1, w1],
    [1, 0],
    [1 - l1, -w1],
    [1 - l2, -w2],
    [0, -w2],
  ]
  return pts.map(([x, y]) => [x * length, y * length])
}

/**
 * Wall (fixed/cantilever) support colours and geometry.
 * Sampled from ppt/media/image1.png and image33.png — the dark charcoal bar
 * is a solid fill, no hatch ticks.
 */
export const WALL = {
  /** Dark charcoal bar colour sampled from the deck reference images. */
  barColor: '#332E27',
  /** Half the bar length in units of `a`. */
  barHalfLength: 0.75,
  /** Bar thickness in units of `a`. */
  barThickness: 0.22,
} as const
