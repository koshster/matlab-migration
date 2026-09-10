import { COLORS, TYPE } from './constants'
import MathLabel from './MathLabel'

interface AxesProps {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

/** plotTruss.m:92-93 — 0 stays "0", ±1 collapse to "a"/"-a", the rest get an "a" suffix. */
function tickLabel(v: number): string {
  if (v === 0) return '0'
  if (v === 1) return 'a'
  if (v === -1) return '-a'
  return `${String(v)}a`
}

function TickLabel({
  v,
  x,
  y,
  anchor,
  baseline,
}: {
  v: number
  x: number
  y: number
  anchor: 'middle' | 'end'
  baseline: 'middle' | 'hanging'
}) {
  return (
    <MathLabel
      x={x}
      y={y}
      label={tickLabel(v)}
      fontSize={TYPE.tickLabel}
      fill={COLORS.tick}
      anchor={anchor}
      baseline={baseline}
    />
  )
}

function range(lo: number, hi: number): number[] {
  const out: number[] = []
  for (let v = lo; v <= hi; v += 1) out.push(v)
  return out
}

/**
 * Unit grid, plot box and a/2a tick labels, matching `plotTruss.m` (`grid on`,
 * `axis equal`, unit ticks). Rendered inside the diagram's flipped group, so
 * coordinates here are physics coordinates.
 */
export default function Axes({ xMin, xMax, yMin, yMax }: AxesProps) {
  const xs = range(xMin, xMax)
  const ys = range(yMin, yMax)
  const hair = 0.008

  return (
    <g>
      {/* The MATLAB axes have a white background; the page around them does not. */}
      <rect x={xMin} y={yMin} width={xMax - xMin} height={yMax - yMin} fill="#ffffff" />

      {xs.map((x) => (
        <line
          key={`gx${String(x)}`}
          x1={x}
          y1={yMin}
          x2={x}
          y2={yMax}
          stroke={COLORS.grid}
          strokeWidth={hair}
        />
      ))}
      {ys.map((y) => (
        <line
          key={`gy${String(y)}`}
          x1={xMin}
          y1={y}
          x2={xMax}
          y2={y}
          stroke={COLORS.grid}
          strokeWidth={hair}
        />
      ))}

      {/* Box: left and bottom are the rulers, top and right stay faint. */}
      <line x1={xMin} y1={yMax} x2={xMax} y2={yMax} stroke={COLORS.axisLight} strokeWidth={hair} />
      <line x1={xMax} y1={yMin} x2={xMax} y2={yMax} stroke={COLORS.axisLight} strokeWidth={hair} />
      <line x1={xMin} y1={yMin} x2={xMin} y2={yMax} stroke={COLORS.axis} strokeWidth={hair * 1.6} />
      <line x1={xMin} y1={yMin} x2={xMax} y2={yMin} stroke={COLORS.axis} strokeWidth={hair * 1.6} />

      {xs.map((x) => (
        <TickLabel key={`tx${String(x)}`} v={x} x={x} y={yMin - 0.1} anchor="middle" baseline="hanging" />
      ))}
      {ys.map((y) => (
        <TickLabel key={`ty${String(y)}`} v={y} x={xMin - 0.1} y={y} anchor="end" baseline="middle" />
      ))}
    </g>
  )
}
