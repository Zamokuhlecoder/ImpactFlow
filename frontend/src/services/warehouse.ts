import { apiClient } from './api'

export interface WarehouseLoad {
  id: string
  transformation_run_id: string
  status: 'running' | 'succeeded' | 'failed' | 'warning'
  records_received: number
  records_loaded: number
  records_skipped: number
  error_details: string | null
  started_at: string
  completed_at: string | null
}

export interface WarehouseOverview {
  dimensions: Record<string, number>
  facts: Record<string, number>
  latest_load: WarehouseLoad | null
  supported_fields: string[]
  unavailable_fields: string[]
}

export interface ProgrammePerformance {
  programme: string
  province: string
  target: number | null
  actual: number | null
  achievement_percentage: number | null
}

export interface ProvincialPerformance {
  province: string
  programmes: number
  participants: number
}

export async function getWarehouseOverview(): Promise<WarehouseOverview> {
  const { data } = await apiClient.get<WarehouseOverview>('/warehouse/overview')
  return data
}

export async function getWarehouseLoads(): Promise<WarehouseLoad[]> {
  const { data } = await apiClient.get<WarehouseLoad[]>('/warehouse/loads')
  return data
}

export async function getProgrammePerformance(): Promise<ProgrammePerformance[]> {
  const { data } = await apiClient.get<ProgrammePerformance[]>('/analytics/programme-performance')
  return data
}

export async function getProvincialPerformance(): Promise<ProvincialPerformance[]> {
  const { data } = await apiClient.get<ProvincialPerformance[]>('/analytics/provincial-performance')
  return data
}
