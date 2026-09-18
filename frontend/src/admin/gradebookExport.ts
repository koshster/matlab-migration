export interface GradebookExportRow {
  displayName: string
  externalId: string
  earned: number | null
}

export interface GradebookExportInput {
  title: string
  rows: GradebookExportRow[]
}

function esc(v: string): string {
  return /[,"\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v
}

/**
 * Builds a Canvas-compatible gradebook CSV string.
 *
 * Canvas matches students by SIS User ID (= our PID / externalId).
 * Empty score cells are ignored on Canvas import, so students whose work
 * is not yet final (earned === null) get a blank cell rather than a 0.
 */
export function buildCanvasCsv(input: GradebookExportInput): string {
  const header = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', input.title]
    .map(esc)
    .join(',')
  const body = input.rows.map((r) =>
    [r.displayName, r.externalId, r.externalId, '', '', r.earned !== null ? String(r.earned) : '']
      .map(esc)
      .join(','),
  )
  return [header, ...body].join('\n')
}
