/**
 * API Configuration Module
 *
 * Centralizes API configuration and URL construction.
 * Uses Vite environment variables for different deployment environments.
 *
 * Environment Variables:
 * - VITE_API_URL: Backend API base URL (default: http://localhost:8080)
 * - VITE_API_TIMEOUT: Request timeout in milliseconds (default: 30000)
 *
 * Usage:
 * ```typescript
 * import { getApiUrl, API_CONFIG } from '@/config/api';
 *
 * // Construct API endpoint URL
 * const url = getApiUrl('/api/projects/start');
 *
 * // Access configuration
 * const timeout = API_CONFIG.timeout;
 * ```
 */

/**
 * API configuration object
 * Populated from environment variables with fallback defaults
 */
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
} as const;

/**
 * Constructs a full API URL from a path
 *
 * @param path - API endpoint path (e.g., '/api/projects/start')
 * @returns Full URL with base URL prepended
 *
 * @example
 * getApiUrl('/api/health')
 * // Returns: 'http://localhost:8080/api/health'
 *
 * @example
 * getApiUrl('api/projects/start') // missing leading slash
 * // Returns: 'http://localhost:8080/api/projects/start'
 */
export const getApiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_CONFIG.baseUrl}${cleanPath}`;
};

/**
 * Type-safe API endpoints
 * Define common endpoints here for autocomplete and refactoring support
 */
export const API_ENDPOINTS = {
  health: '/api/health',
  projectStart: '/api/projects/start',
  taskApprove: '/api/tasks/approve',
} as const;
