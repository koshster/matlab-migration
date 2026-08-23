import type { components } from '@statics/contract/src/index'

type RosterImportEntry = components['schemas']['RosterImportEntry']

export interface ParsedRoster {
  entries: RosterImportEntry[]
  /** 1-based line numbers that were skipped, with a reason. */
  skipped: { line: number; text: string; reason: string }[]
}

/** Header aliases we accept, normalized to lowercase with non-letters stripped. */
const HEADER_ALIASES: Record<string, keyof RosterImportEntry> = {
  pid: 'pid',
  studentid: 'pid',
  id: 'pid',
  sisuserid: 'pid',
  sisloginid: 'pid',
  email: 'email',
  emailaddress: 'email',
  firstname: 'firstName',
  first: 'firstName',
  givenname: 'firstName',
  lastname: 'lastName',
  last: 'lastName',
  surname: 'lastName',
  familyname: 'lastName',
}

const canonical = (header: string) => header.toLowerCase().replace(/[^a-z]/g, '')

/**
 * A PID is a single token. Without this, a header-mapped first column would
 * accept free text — "nonsense line" became the PID "NONSENSE LINE" and was
 * silently invited.
 */
function looksLikePid(value: string): boolean {
  return value !== '' && !/[\s,]/.test(value)
}

function looksLikeEmail(value: string): boolean {
  if (!value || /\s/.test(value)) return false
  const at = value.lastIndexOf('@')
  if (at <= 0 || at === value.length - 1) return false
  const domain = value.slice(at + 1)
  return domain.includes('.') && !domain.startsWith('.') && !domain.endsWith('.')
}

/**
 * Split one CSV line, honouring double-quoted fields so a quoted
 * "Lovelace, Ada" stays a single cell.
 */
function splitRow(line: string): string[] {
  const cells: string[] = []
  let cell = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cell += '"'
          i += 1
        } else {
          inQuotes = false
        }
      } else {
        cell += ch
      }
    } else if (ch === '"') {
      inQuotes = true
    } else if (ch === ',' || ch === '\t' || ch === ';') {
      cells.push(cell)
      cell = ''
    } else {
      cell += ch
    }
  }
  cells.push(cell)
  return cells.map((c) => c.trim())
}

/** Canvas-style "Lovelace, Ada" → { firstName: 'Ada', lastName: 'Lovelace' } */
function splitFullName(value: string): { firstName?: string; lastName?: string } {
  if (value.includes(',')) {
    const [last, first] = value.split(',', 2)
    return { firstName: first.trim() || undefined, lastName: last.trim() || undefined }
  }
  const parts = value.split(/\s+/).filter(Boolean)
  if (parts.length === 0) return {}
  if (parts.length === 1) return { firstName: parts[0] }
  return { firstName: parts[0], lastName: parts.slice(1).join(' ') }
}

/**
 * Parse a pasted roster.
 *
 * Accepts a header row (in any column order, using the aliases above) or no
 * header at all, in which case each cell is classified by shape: anything
 * email-looking becomes the email, the remaining token becomes the PID, and
 * leftover text is treated as a name. Blank lines are ignored; rows with
 * neither a PID nor an email are reported in `skipped` rather than dropped
 * silently, because a quietly-shortened roster is how students go missing.
 */
export function parseRosterCsv(input: string): ParsedRoster {
  const entries: RosterImportEntry[] = []
  const skipped: ParsedRoster['skipped'] = []

  const rawLines = input.split(/\r?\n/)
  let columns: (keyof RosterImportEntry | 'fullName' | null)[] | null = null

  rawLines.forEach((raw, idx) => {
    const line = raw.trim()
    const lineNo = idx + 1
    if (!line) return

    const cells = splitRow(line)

    // Detect a header row, but only on the first non-blank line.
    if (columns === null) {
      const mapped = cells.map((c) => {
        const key = canonical(c)
        if (key === 'name' || key === 'fullname' || key === 'student') return 'fullName' as const
        return HEADER_ALIASES[key] ?? null
      })
      const recognized = mapped.filter(Boolean).length
      if (recognized >= 2 || (recognized === 1 && cells.length === 1)) {
        columns = mapped
        return
      }
      columns = []
    }

    const entry: RosterImportEntry = {}

    if (columns.length > 0) {
      columns.forEach((key, i) => {
        const value = cells[i]
        if (!key || !value) return
        if (key === 'fullName') {
          const { firstName, lastName } = splitFullName(value)
          if (firstName) entry.firstName = firstName
          if (lastName) entry.lastName = lastName
        } else if (key === 'pid') {
          // Free text in the PID column is a mis-shaped row, not an identifier.
          if (looksLikePid(value)) entry.pid = value
        } else {
          entry[key] = value
        }
      })
    } else {
      // Headerless: classify by shape.
      const remaining: string[] = []
      cells.filter(Boolean).forEach((value) => {
        if (!entry.email && looksLikeEmail(value)) entry.email = value
        else remaining.push(value)
      })
      if (remaining.length === 1 && remaining[0]) {
        const only = remaining[0]
        // A lone token with a space is a name, not a PID.
        if (/\s|,/.test(only)) Object.assign(entry, splitFullName(only))
        else entry.pid = only
      } else if (remaining.length > 1) {
        entry.pid = remaining[0]
        const rest = remaining.slice(1).join(' ')
        Object.assign(entry, splitFullName(rest))
      }
    }

    if (entry.email) entry.email = entry.email.toLowerCase()
    if (entry.pid) entry.pid = entry.pid.toUpperCase()

    if (!entry.pid && !entry.email) {
      skipped.push({ line: lineNo, text: line, reason: 'no PID or email found' })
      return
    }
    if (entry.email && !looksLikeEmail(entry.email)) {
      skipped.push({ line: lineNo, text: line, reason: `"${entry.email}" is not a valid email` })
      return
    }
    entries.push(entry)
  })

  return { entries, skipped }
}
