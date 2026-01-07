/**
 * Server Manager Utilities for E2E Testing
 *
 * Provides utilities for starting and stopping backend/frontend servers
 * during integration tests. Ensures proper cleanup and health checking.
 *
 * Usage:
 * ```typescript
 * beforeAll(async () => {
 *   await startBackend();
 *   await startFrontend();
 * });
 *
 * afterAll(async () => {
 *   await stopServers();
 * });
 * ```
 */

import { ChildProcess, spawn } from 'child_process';
import { resolve } from 'path';

// Server configuration
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5173;
const BACKEND_URL = process.env.VITE_API_URL || `http://localhost:${BACKEND_PORT}`;
const FRONTEND_URL = process.env.VITE_FRONTEND_URL || `http://localhost:${FRONTEND_PORT}`;

// Paths
const BACKEND_DIR = resolve(__dirname, '../../../backend');
const FRONTEND_DIR = resolve(__dirname, '../..');

// Process references
let backendProcess: ChildProcess | null = null;
let frontendProcess: ChildProcess | null = null;

// Health check configuration
const HEALTH_CHECK_RETRIES = 30; // 30 retries
const HEALTH_CHECK_INTERVAL = 1000; // 1 second between retries

/**
 * Check if a server is healthy by pinging its health endpoint
 */
async function checkHealth(url: string, endpoint = '/api/health'): Promise<boolean> {
  try {
    const response = await fetch(`${url}${endpoint}`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Wait for server to become healthy
 */
async function waitForHealth(
  url: string,
  serverName: string,
  endpoint = '/api/health'
): Promise<void> {
  console.log(`⏳ Waiting for ${serverName} to become healthy at ${url}...`);

  for (let i = 0; i < HEALTH_CHECK_RETRIES; i++) {
    const healthy = await checkHealth(url, endpoint);

    if (healthy) {
      console.log(`✅ ${serverName} is healthy (attempt ${i + 1}/${HEALTH_CHECK_RETRIES})`);
      return;
    }

    console.log(`⏳ ${serverName} not ready yet (attempt ${i + 1}/${HEALTH_CHECK_RETRIES})`);
    await new Promise((resolve) => setTimeout(resolve, HEALTH_CHECK_INTERVAL));
  }

  throw new Error(
    `❌ ${serverName} failed to become healthy after ${HEALTH_CHECK_RETRIES} attempts`
  );
}

/**
 * Check if a port is already in use
 */
async function isPortInUse(port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://localhost:${port}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Start the FastAPI backend server
 *
 * Activates Python virtual environment and runs uvicorn.
 * Waits for health endpoint to respond before returning.
 *
 * @throws Error if server fails to start or health check fails
 */
export async function startBackend(): Promise<void> {
  console.log('🚀 Starting backend server...');

  // Check if backend is already running
  const alreadyRunning = await isPortInUse(BACKEND_PORT);
  if (alreadyRunning) {
    console.log(`ℹ️  Backend already running on port ${BACKEND_PORT}`);
    return;
  }

  // Activate venv and start uvicorn
  const activateVenv = `source venv/bin/activate`;
  const startUvicorn = `uvicorn src.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --reload`;
  const command = `${activateVenv} && ${startUvicorn}`;

  backendProcess = spawn('bash', ['-c', command], {
    cwd: BACKEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
  });

  // Log backend output (for debugging)
  backendProcess.stdout?.on('data', (data) => {
    const output = data.toString();
    if (output.includes('Application startup complete')) {
      console.log('✅ Backend startup complete');
    }
  });

  backendProcess.stderr?.on('data', (data) => {
    const error = data.toString();
    // Only log critical errors, not INFO logs from uvicorn
    if (!error.includes('INFO:') && !error.includes('WARNING:')) {
      console.error('Backend error:', error);
    }
  });

  backendProcess.on('error', (error) => {
    console.error('❌ Backend process error:', error);
  });

  // Wait for backend to become healthy
  await waitForHealth(BACKEND_URL, 'Backend');
}

/**
 * Start the Vite frontend development server
 *
 * Runs npm run dev and waits for server to respond.
 *
 * @throws Error if server fails to start or health check fails
 */
export async function startFrontend(): Promise<void> {
  console.log('🚀 Starting frontend server...');

  // Check if frontend is already running
  const alreadyRunning = await isPortInUse(FRONTEND_PORT);
  if (alreadyRunning) {
    console.log(`ℹ️  Frontend already running on port ${FRONTEND_PORT}`);
    return;
  }

  // Start Vite dev server
  frontendProcess = spawn('npm', ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
    env: {
      ...process.env,
      PORT: String(FRONTEND_PORT),
    },
  });

  // Log frontend output (for debugging)
  frontendProcess.stdout?.on('data', (data) => {
    const output = data.toString();
    if (output.includes('Local:') || output.includes('ready in')) {
      console.log('✅ Frontend startup complete');
    }
  });

  frontendProcess.stderr?.on('data', (data) => {
    const error = data.toString();
    // Vite logs to stderr even for non-errors
    if (!error.includes('ready in') && !error.includes('Local:')) {
      console.error('Frontend error:', error);
    }
  });

  frontendProcess.on('error', (error) => {
    console.error('❌ Frontend process error:', error);
  });

  // Wait for frontend to become healthy
  // Note: Vite doesn't have a health endpoint, so we check the root page
  await waitForHealth(FRONTEND_URL, 'Frontend', '/');
}

/**
 * Stop all running servers
 *
 * Gracefully shuts down backend and frontend processes.
 * Waits for processes to exit before returning.
 */
export async function stopServers(): Promise<void> {
  console.log('🛑 Stopping servers...');

  const stopPromises: Promise<void>[] = [];

  // Stop backend
  if (backendProcess && !backendProcess.killed) {
    stopPromises.push(
      new Promise<void>((resolve) => {
        backendProcess!.on('exit', () => {
          console.log('✅ Backend stopped');
          resolve();
        });

        // Kill the entire process group (detached processes)
        if (backendProcess!.pid) {
          process.kill(-backendProcess!.pid, 'SIGTERM');
        }

        // Fallback: Force kill after 5 seconds
        setTimeout(() => {
          if (backendProcess && !backendProcess.killed && backendProcess.pid) {
            process.kill(-backendProcess.pid, 'SIGKILL');
            resolve();
          }
        }, 5000);
      })
    );
  }

  // Stop frontend
  if (frontendProcess && !frontendProcess.killed) {
    stopPromises.push(
      new Promise<void>((resolve) => {
        frontendProcess!.on('exit', () => {
          console.log('✅ Frontend stopped');
          resolve();
        });

        // Kill the entire process group (detached processes)
        if (frontendProcess!.pid) {
          process.kill(-frontendProcess!.pid, 'SIGTERM');
        }

        // Fallback: Force kill after 5 seconds
        setTimeout(() => {
          if (frontendProcess && !frontendProcess.killed && frontendProcess.pid) {
            process.kill(-frontendProcess.pid, 'SIGKILL');
            resolve();
          }
        }, 5000);
      })
    );
  }

  // Wait for all processes to stop
  await Promise.all(stopPromises);

  backendProcess = null;
  frontendProcess = null;

  console.log('✅ All servers stopped');
}

/**
 * Cleanup handler for unexpected termination
 *
 * Ensures servers are stopped even if test suite crashes
 */
process.on('SIGINT', async () => {
  console.log('\n⚠️  Received SIGINT, cleaning up...');
  await stopServers();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n⚠️  Received SIGTERM, cleaning up...');
  await stopServers();
  process.exit(0);
});

process.on('uncaughtException', async (error) => {
  console.error('❌ Uncaught exception:', error);
  await stopServers();
  process.exit(1);
});

// Export server URLs for use in tests
export { BACKEND_URL, FRONTEND_URL, BACKEND_PORT, FRONTEND_PORT };
