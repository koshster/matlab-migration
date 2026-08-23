import { describe, it, expect } from 'vitest'
import { parseRosterCsv } from './rosterCsv'

describe('parseRosterCsv', () => {
  it('reads a header row in any column order', () => {
    const { entries, skipped } = parseRosterCsv(
      ['Email,Student ID,Last Name,First Name', 'ada@ucsd.edu,a1234567,Lovelace,Ada'].join('\n'),
    )
    expect(skipped).toEqual([])
    expect(entries).toEqual([
      { email: 'ada@ucsd.edu', pid: 'A1234567', lastName: 'Lovelace', firstName: 'Ada' },
    ])
  })

  it('normalizes PID to upper and email to lower so invites match', () => {
    const { entries } = parseRosterCsv('PID,Email\n  a999  ,  ADA@UCSD.EDU  ')
    expect(entries[0]).toEqual({ pid: 'A999', email: 'ada@ucsd.edu' })
  })

  it('handles a Canvas-style quoted "Last, First" name cell', () => {
    const { entries } = parseRosterCsv('Name,SIS User ID\n"Lovelace, Ada",A1234567')
    expect(entries[0]).toEqual({ firstName: 'Ada', lastName: 'Lovelace', pid: 'A1234567' })
  })

  it('accepts a bare list of PIDs with no header', () => {
    const { entries } = parseRosterCsv('A111\nA222\nA333')
    expect(entries).toEqual([{ pid: 'A111' }, { pid: 'A222' }, { pid: 'A333' }])
  })

  it('accepts a bare list of emails with no header', () => {
    const { entries } = parseRosterCsv('ada@ucsd.edu\ngrace@ucsd.edu')
    expect(entries).toEqual([{ email: 'ada@ucsd.edu' }, { email: 'grace@ucsd.edu' }])
  })

  it('classifies headerless mixed columns by shape', () => {
    const { entries } = parseRosterCsv('A111,ada@ucsd.edu,Ada Lovelace')
    expect(entries[0]).toEqual({
      pid: 'A111',
      email: 'ada@ucsd.edu',
      firstName: 'Ada',
      lastName: 'Lovelace',
    })
  })

  it('ignores blank lines and tolerates tabs and semicolons', () => {
    const { entries, skipped } = parseRosterCsv('A111\n\n\tA222\t\n\nA333;ada@ucsd.edu\n')
    expect(skipped).toEqual([])
    expect(entries).toEqual([
      { pid: 'A111' },
      { pid: 'A222' },
      { pid: 'A333', email: 'ada@ucsd.edu' },
    ])
  })

  it('reports unusable rows instead of silently dropping them', () => {
    // A silently-shortened roster is how students go missing.
    const { entries, skipped } = parseRosterCsv('A111\nJust A Name\nA222')
    expect(entries).toEqual([{ pid: 'A111' }, { pid: 'A222' }])
    expect(skipped).toHaveLength(1)
    expect(skipped[0]).toMatchObject({ line: 2, reason: 'no PID or email found' })
  })

  it('rejects a malformed email rather than inviting into the void', () => {
    const { entries, skipped } = parseRosterCsv('Email\nnot-an-email')
    expect(entries).toEqual([])
    expect(skipped[0]?.reason).toContain('not a valid email')
  })

  it('does not mistake a single-column header for data', () => {
    const { entries } = parseRosterCsv('PID\nA111\nA222')
    expect(entries).toEqual([{ pid: 'A111' }, { pid: 'A222' }])
  })

  it('treats an unrecognized first row as data, not a header', () => {
    const { entries } = parseRosterCsv('A111\nA222')
    expect(entries).toHaveLength(2)
  })

  it('rejects free text in a headed PID column', () => {
    // Regression: this used to be invited as the PID "NONSENSE LINE".
    const { entries, skipped } = parseRosterCsv(
      ['PID,Email', 'A111,ada@ucsd.edu', 'nonsense line'].join('\n'),
    )
    expect(entries).toEqual([{ pid: 'A111', email: 'ada@ucsd.edu' }])
    expect(skipped).toHaveLength(1)
    expect(skipped[0]).toMatchObject({ line: 3, reason: 'no PID or email found' })
  })

  it('keeps a row whose PID column is free text but which has a valid email', () => {
    const { entries, skipped } = parseRosterCsv(
      ['PID,Email', 'not a pid,ada@ucsd.edu'].join('\n'),
    )
    expect(skipped).toEqual([])
    expect(entries).toEqual([{ email: 'ada@ucsd.edu' }])
  })

  it('returns nothing for empty input', () => {
    expect(parseRosterCsv('   \n\n')).toEqual({ entries: [], skipped: [] })
  })
})
