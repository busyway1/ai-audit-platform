/**
 * E2E Test Setup Utilities
 *
 * Provides utilities for managing backend and frontend servers during E2E tests.
 * Handles server startup, health checks, and graceful shutdown.
 */

import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';

const sleep = promisify(setTimeout);

/**
 * Backend server configuration
 */
export const BACKEND_CONFIG = {
  url: process.env.VITE_API_URL || 'http://localhost:8000',
  healthEndpoint: '/api/health',
  startupTimeout: Number(process.env.VITE_API_TIMEOUT) || 30000,
  port: 8000,
};

/**
 * Frontend server configuration
 */
export const FRONTEND_CONFIG = {
  url: process.env.VITE_FRONTEND_URL || 'http://localhost:5173',
  startupTimeout: 30000,
  port: 5173,
};

/**
 * Check if a server is healthy by polling its health endpoint
 */
export async function waitForServer(
  url: string,
  timeout: number = 30000
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        console.log(`✅ Server at ${url} is healthy`);
        return true;
      }
    } catch (error) {
      // Server not ready yet, continue polling
    }

    await sleep(1000); // Poll every second
  }

  console.error(`❌ Server at ${url} failed to become healthy within ${timeout}ms`);
  return false;
}

/**
 * Check if backend server is running
 */
export async function isBackendRunning(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_CONFIG.url}${BACKEND_CONFIG.healthEndpoint}`, {
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Check if frontend server is running
 */
export async function isFrontendRunning(): Promise<boolean> {
  try {
    const response = await fetch(FRONTEND_CONFIG.url, {
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Start backend server
 * Note: In most cases, you should start the backend manually before running tests.
 * This function is provided for advanced use cases.
 */
export async function startBackendServer(): Promise<ChildProcess | null> {
  console.log('Starting backend server...');

  // Check if already running
  if (await isBackendRunning()) {
    console.log('Backend server already running');
    return null;
  }

  // Start server
  const backendProcess = spawn('uvicorn', ['src.main:app', '--reload', '--port', '8000'], {
    cwd: process.cwd().replace('/frontend', '/backend'),
    detached: true,
    stdio: 'ignore',
  });

  // Wait for server to be healthy
  const isHealthy = await waitForServer(
    `${BACKEND_CONFIG.url}${BACKEND_CONFIG.healthEndpoint}`,
    BACKEND_CONFIG.startupTimeout
  );

  if (!isHealthy) {
    backendProcess.kill();
    throw new Error('Backend server failed to start');
  }

  return backendProcess;
}

/**
 * Stop a server process gracefully
 */
export function stopServer(process: ChildProcess | null): void {
  if (process && !process.killed) {
    process.kill('SIGTERM');
    console.log('Server stopped');
  }
}

/**
 * Global test setup - verify both servers are running
 */
export async function globalSetup(): Promise<void> {
  console.log('========================================');
  console.log('E2E Test Global Setup');
  console.log('========================================');

  // Check backend
  const backendRunning = await isBackendRunning();
  if (!backendRunning) {
    console.warn('⚠️  Backend server not running at', BACKEND_CONFIG.url);
    console.warn('   Please start backend manually:');
    console.warn('   cd backend && source venv/bin/activate && python -m src.main');
  } else {
    console.log('✅ Backend server is running');
  }

  // Frontend will be started automatically by Playwright webServer config
  console.log('✅ Frontend server will be started by Playwright');

  console.log('========================================');
}

/**
 * Global test teardown
 */
export async function globalTeardown(): Promise<void> {
  console.log('E2E Test Global Teardown');
  // Cleanup if needed
}
