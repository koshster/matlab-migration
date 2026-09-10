/**
 * plotTruss.m:135 (`focus`) — one unit of clearance past the extreme nodes,
 * snapped to the grid so the window edges land on gridlines.
 */
export interface Window {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

export function plotWindow(points: Array<{ x: number; y: number }>): Window {
  if (points.length === 0) return { xMin: -1, xMax: 1, yMin: -1, yMax: 1 }
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  return {
    xMin: Math.floor(Math.min(...xs)) - 1,
    xMax: Math.ceil(Math.max(...xs)) + 1,
    yMin: Math.floor(Math.min(...ys)) - 1,
    yMax: Math.ceil(Math.max(...ys)) + 1,
  }
}
