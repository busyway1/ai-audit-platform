/**
 * Backend API Helper Utilities
 *
 * Provides type-safe helper functions for interacting with the backend API
 * during E2E tests. Handles authentication, request formatting, and response parsing.
 */

import { BACKEND_CONFIG } from './setup';

/**
 * Base API client configuration
 */
const API_BASE_URL = BACKEND_CONFIG.url;

/**
 * API response type for health check
 */
export interface HealthCheckResponse {
  status: string;
  timestamp?: string;
  services?: {
    database?: string;
    langgraph?: string;
  };
}

/**
 * API response type for project start
 */
export interface StartProjectResponse {
  task_id: string;
  status: string;
  message: string;
}

/**
 * API response type for task approval
 */
export interface ApproveTaskResponse {
  task_id: string;
  status: string;
  approved_at: string;
}

/**
 * Generic API error response
 */
export interface ApiError {
  detail: string;
  status_code?: number;
}

/**
 * Helper to make API requests with proper error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
        status_code: response.status,
      }));
      throw new Error(error.detail);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`API request failed: ${String(error)}`);
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<HealthCheckResponse> {
  return apiRequest<HealthCheckResponse>('/api/health');
}

/**
 * Start a new audit project
 */
export async function startProject(data: {
  project_name: string;
  client_name: string;
  audit_type: string;
}): Promise<StartProjectResponse> {
  return apiRequest<StartProjectResponse>('/api/projects/start', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Approve a task
 */
export async function approveTask(taskId: string): Promise<ApproveTaskResponse> {
  return apiRequest<ApproveTaskResponse>('/api/tasks/approve', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId }),
  });
}

/**
 * Get task status via SSE stream
 * Note: This returns a readable stream. Use in tests with care.
 */
export function getTaskStream(taskId: string): EventSource {
  const url = `${API_BASE_URL}/stream/${taskId}`;
  return new EventSource(url);
}

/**
 * Wait for backend to be ready
 */
export async function waitForBackendReady(
  timeout: number = 30000
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const health = await checkHealth();
      if (health.status === 'healthy' || health.status === 'ok') {
        return true;
      }
    } catch {
      // Backend not ready, continue polling
    }

    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  return false;
}

/**
 * Helper to check if an endpoint returns expected status code
 */
export async function checkEndpointStatus(
  endpoint: string,
  expectedStatus: number = 200
): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    return response.status === expectedStatus;
  } catch {
    return false;
  }
}

/**
 * Mock SSE event listener for testing
 */
export class MockSSEListener {
  private eventSource: EventSource;
  private events: Array<{ type: string; data: string }> = [];

  constructor(taskId: string) {
    this.eventSource = getTaskStream(taskId);
  }

  start(): void {
    this.eventSource.onmessage = (event) => {
      this.events.push({ type: 'message', data: event.data });
    };

    this.eventSource.onerror = () => {
      this.events.push({ type: 'error', data: 'Stream error' });
    };
  }

  getEvents(): Array<{ type: string; data: string }> {
    return this.events;
  }

  stop(): void {
    this.eventSource.close();
  }
}
