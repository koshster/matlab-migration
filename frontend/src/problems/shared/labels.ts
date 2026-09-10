/**
 * Force-label renderer helpers.
 *
 * "3F" → { head: "3", unit: true }
 * "F"  → { head: "",  unit: true }
 * "nF" → { head: "n", unit: true } for any numeric prefix
 *
 * Render with:
 *   <FlipText ...>{head}<tspan fontStyle="italic">F</tspan></FlipText>
 */
export function splitLabel(label: string): { head: string; unit: boolean } {
  if (label.endsWith('F')) return { head: label.slice(0, -1), unit: true }
  return { head: label, unit: false }
}
