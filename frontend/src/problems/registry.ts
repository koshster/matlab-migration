import { lazy, type ComponentType } from 'react'
import FallbackDiagram from './FallbackDiagram'

const registry: Record<string, ComponentType<{ geometry: unknown }>> = {
  truss: lazy(() => import('./truss/TrussDiagram')),
}

export function getRenderer(problemType: string): ComponentType<{ geometry: unknown }> {
  return registry[problemType] ?? FallbackDiagram
}
