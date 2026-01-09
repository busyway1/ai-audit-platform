/**
 * Dashboard Data Hook
 *
 * Fetches dashboard metrics from the backend API with graceful error handling.
 * Falls back to mock data when the API is unavailable or in demo mode.
 *
 * Features:
 * - Fetches from /api/dashboard/metrics endpoint
 * - Loading, error, and data states
 * - Automatic fallback to mock data on error
 * - Configurable refresh interval
 * - Demo mode support
 *
 * @module hooks/useDashboard
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { getApiUrl } from '@/config/api'
import { tasks as mockTasks, agents as mockAgents, riskHeatmap as mockRiskHeatmap } from '../data/mockData'
import type { Task, Agent, RiskHeatmapItem } from '../types/audit'

/**
 * Recent activity item from the API
 */
export interface RecentActivity {
  id: string
  type: 'task_completed' | 'task_started' | 'risk_alert' | 'agent_status_change' | 'document_uploaded'
  title: string
  description: string
  timestamp: string
  metadata?: Record<string, unknown>
}

/**
 * Dashboard metrics response from the API
 */
export interface DashboardMetrics {
  activeProjects: number
  pendingTasks: number
  completedAudits: number
  riskAlerts: number
  recentActivities: RecentActivity[]
}

/**
 * Extended dashboard data including computed values
 */
export interface DashboardData {
  metrics: DashboardMetrics
  tasks: Task[]
  agents: Agent[]
  riskHeatmap: RiskHeatmapItem[]
  overallProgress: number
  completedTasks: number
  inProgressTasks: number
  highRiskIssues: number
  totalTasks: number
}

/**
 * Hook options
 */
interface UseDashboardOptions {
  /** Enable demo/mock mode (default: false) */
  demoMode?: boolean
  /** Auto-refresh interval in milliseconds (default: 0 = disabled) */
  refreshInterval?: number
  /** Callback when data is refreshed */
  onRefresh?: () => void
  /** Callback when error occurs */
  onError?: (error: Error) => void
}

/**
 * Hook return type
 */
interface UseDashboardReturn {
  /** Dashboard data (null while loading initially) */
  data: DashboardData | null
  /** Whether data is currently being fetched */
  isLoading: boolean
  /** Any error that occurred during fetch */
  error: Error | null
  /** Whether using mock/fallback data */
  isUsingMockData: boolean
  /** Manually trigger a refresh */
  refresh: () => Promise<void>
  /** Last successful fetch timestamp */
  lastUpdated: Date | null
}

/**
 * Calculate computed dashboard values from tasks
 */
function calculateDashboardMetrics(tasks: Task[]): {
  overallProgress: number
  completedTasks: number
  inProgressTasks: number
  highRiskIssues: number
  totalTasks: number
} {
  const totalTasks = tasks.length
  const completedTasks = tasks.filter(t => t.status === 'completed').length
  const inProgressTasks = tasks.filter(t => t.status === 'in-progress').length
  const highRiskIssues = tasks.filter(t => t.riskLevel === 'critical' || t.riskLevel === 'high').length
  const overallProgress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0

  return {
    overallProgress,
    completedTasks,
    inProgressTasks,
    highRiskIssues,
    totalTasks,
  }
}

/**
 * Generate default metrics from mock data
 */
function getDefaultMetrics(): DashboardMetrics {
  return {
    activeProjects: 5,
    pendingTasks: mockTasks.filter(t => t.status !== 'completed').length,
    completedAudits: 8,
    riskAlerts: mockTasks.filter(t => t.riskLevel === 'critical' || t.riskLevel === 'high').length,
    recentActivities: [],
  }
}

/**
 * Generate fallback dashboard data from mock data
 */
function getFallbackData(): DashboardData {
  const computed = calculateDashboardMetrics(mockTasks)
  return {
    metrics: getDefaultMetrics(),
    tasks: mockTasks,
    agents: mockAgents,
    riskHeatmap: mockRiskHeatmap,
    ...computed,
  }
}

/**
 * Hook for fetching and managing dashboard data
 *
 * This hook provides:
 * 1. Automatic fetching from /api/dashboard/metrics
 * 2. Graceful error handling with mock data fallback
 * 3. Loading and error states
 * 4. Optional auto-refresh capability
 *
 * @param options - Configuration options
 * @returns Dashboard data, loading state, error, and refresh function
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const { data, isLoading, error, refresh } = useDashboard({
 *     refreshInterval: 30000, // Auto-refresh every 30 seconds
 *   })
 *
 *   if (isLoading && !data) {
 *     return <DashboardSkeleton />
 *   }
 *
 *   return (
 *     <div>
 *       <h1>Progress: {data.overallProgress}%</h1>
 *       <button onClick={refresh}>Refresh</button>
 *     </div>
 *   )
 * }
 * ```
 */
export function useDashboard(options: UseDashboardOptions = {}): UseDashboardReturn {
  const {
    demoMode = false,
    refreshInterval = 0,
    onRefresh,
    onError,
  } = options

  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [isUsingMockData, setIsUsingMockData] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const isMountedRef = useRef(true)
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  /**
   * Fetch dashboard data from API
   */
  const fetchDashboard = useCallback(async (): Promise<void> => {
    // In demo mode, use mock data directly
    if (demoMode) {
      const fallbackData = getFallbackData()
      if (isMountedRef.current) {
        setData(fallbackData)
        setIsLoading(false)
        setIsUsingMockData(true)
        setLastUpdated(new Date())
        onRefresh?.()
      }
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(getApiUrl('/api/dashboard/metrics'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Dashboard API error: ${response.status} ${response.statusText}`)
      }

      const apiMetrics: DashboardMetrics = await response.json()

      if (!isMountedRef.current) return

      // Combine API metrics with local task/agent data
      // In a full implementation, these would also come from the API
      const computed = calculateDashboardMetrics(mockTasks)

      const dashboardData: DashboardData = {
        metrics: apiMetrics,
        tasks: mockTasks,
        agents: mockAgents,
        riskHeatmap: mockRiskHeatmap,
        ...computed,
      }

      setData(dashboardData)
      setIsUsingMockData(false)
      setLastUpdated(new Date())
      onRefresh?.()

    } catch (err) {
      const fetchError = err instanceof Error ? err : new Error('Failed to fetch dashboard data')

      if (!isMountedRef.current) return

      console.warn('[useDashboard] API fetch failed, falling back to mock data:', fetchError.message)

      // Fallback to mock data on error
      const fallbackData = getFallbackData()
      setData(fallbackData)
      setError(fetchError)
      setIsUsingMockData(true)
      setLastUpdated(new Date())
      onError?.(fetchError)

    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [demoMode, onRefresh, onError])

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async (): Promise<void> => {
    await fetchDashboard()
  }, [fetchDashboard])

  // Initial fetch on mount
  useEffect(() => {
    isMountedRef.current = true
    fetchDashboard()

    return () => {
      isMountedRef.current = false
    }
  }, [fetchDashboard])

  // Set up auto-refresh interval
  useEffect(() => {
    if (refreshInterval > 0) {
      refreshIntervalRef.current = setInterval(() => {
        if (isMountedRef.current) {
          fetchDashboard()
        }
      }, refreshInterval)
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
    }
  }, [refreshInterval, fetchDashboard])

  return {
    data,
    isLoading,
    error,
    isUsingMockData,
    refresh,
    lastUpdated,
  }
}

export default useDashboard
