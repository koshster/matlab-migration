import { describe, it, expect } from 'vitest'
import { buildCanvasCsv } from './gradebookExport'

describe('buildCanvasCsv', () => {
  it('produces a header with the 6 Canvas reserved columns plus the assignment title', () => {
    const csv = buildCanvasCsv({ title: 'Homework 1', rows: [] })
    const header = csv.split('\n')[0]
    expect(header).toBe('Student,ID,SIS User ID,SIS Login ID,Section,Homework 1')
  })

  it('emits one row per student', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [
        { displayName: 'Alice Zhao', externalId: 'AZ123', earned: 8 },
        { displayName: 'Bob Smith', externalId: 'BS456', earned: 5 },
      ],
    })
    const lines = csv.split('\n')
    expect(lines).toHaveLength(3) // header + 2 data rows
  })

  it('places earned score in the last column', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [{ displayName: 'Alice Zhao', externalId: 'AZ123', earned: 8 }],
    })
    const dataRow = csv.split('\n')[1]
    expect(dataRow.endsWith(',8')).toBe(true)
  })

  it('leaves score cell empty when earned is null', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [{ displayName: 'Alice Zhao', externalId: 'AZ123', earned: null }],
    })
    const dataRow = csv.split('\n')[1]
    expect(dataRow.endsWith(',')).toBe(true)
  })

  it('double-quotes names that contain commas', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [{ displayName: 'Lovelace, Ada', externalId: 'LA999', earned: 10 }],
    })
    const dataRow = csv.split('\n')[1]
    expect(dataRow.startsWith('"Lovelace, Ada"')).toBe(true)
  })

  it('double-quotes the column header when the title contains a comma', () => {
    const csv = buildCanvasCsv({ title: 'Unit 1, Part 2', rows: [] })
    const header = csv.split('\n')[0]
    expect(header.endsWith('"Unit 1, Part 2"')).toBe(true)
  })

  it('escapes embedded double-quotes per RFC 4180', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [{ displayName: 'O"Brien Pat', externalId: 'OP1', earned: 7 }],
    })
    const dataRow = csv.split('\n')[1]
    expect(dataRow.startsWith('"O""Brien Pat"')).toBe(true)
  })

  it('maps externalId to both ID and SIS User ID columns', () => {
    const csv = buildCanvasCsv({
      title: 'HW1',
      rows: [{ displayName: 'Alice Zhao', externalId: 'AZ123', earned: 8 }],
    })
    const cells = csv.split('\n')[1].split(',')
    expect(cells[1]).toBe('AZ123') // ID
    expect(cells[2]).toBe('AZ123') // SIS User ID
  })

  it('handles an empty roster without throwing', () => {
    const csv = buildCanvasCsv({ title: 'HW1', rows: [] })
    expect(csv).toBe('Student,ID,SIS User ID,SIS Login ID,Section,HW1')
  })
})
