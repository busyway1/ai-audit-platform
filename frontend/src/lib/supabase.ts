/**
 * Supabase Client Configuration
 *
 * This module initializes and exports a typed Supabase client for the AI Audit Platform.
 * It uses environment variables for configuration and provides type-safe access to the database.
 *
 * Environment variables required:
 * - VITE_SUPABASE_URL: Your Supabase project URL
 * - VITE_SUPABASE_ANON_KEY: Your Supabase anonymous/public API key
 *
 * @module lib/supabase
 */

import { createClient } from '@supabase/supabase-js'
import type { Database } from '../app/types/supabase'

// Validate environment variables at module load time
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl) {
  throw new Error(
    'Missing VITE_SUPABASE_URL environment variable. ' +
    'Please check your .env file and ensure it matches .env.example'
  )
}

if (!supabaseAnonKey) {
  throw new Error(
    'Missing VITE_SUPABASE_ANON_KEY environment variable. ' +
    'Please check your .env file and ensure it matches .env.example'
  )
}

/**
 * Typed Supabase client instance
 *
 * This client is configured with:
 * - Automatic session persistence in localStorage
 * - Realtime subscriptions enabled
 * - Type-safe database operations via Database type
 *
 * Usage:
 * ```typescript
 * import { supabase } from '@/lib/supabase';
 *
 * // Type-safe queries
 * const { data, error } = await supabase
 *   .from('audit_tasks')
 *   .select('*')
 *   .eq('status', 'In-Progress');
 * ```
 */
export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    storageKey: 'ai-audit-auth',
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
  realtime: {
    params: {
      eventsPerSecond: 10, // Throttle realtime events to avoid overwhelming the UI
    },
  },
  global: {
    headers: {
      'X-Client-Info': 'ai-audit-platform@1.0.0',
    },
  },
})

/**
 * Helper function to check Supabase connection health
 *
 * @returns Promise resolving to true if connection is healthy
 */
export async function checkSupabaseHealth(): Promise<boolean> {
  try {
    const { error } = await supabase.from('audit_projects').select('count', { count: 'exact', head: true })
    return !error
  } catch {
    return false
  }
}

/**
 * Helper function to get the current authenticated user
 *
 * @returns Promise resolving to user object or null
 */
export async function getCurrentUser() {
  const { data: { user }, error } = await supabase.auth.getUser()
  if (error) {
    console.error('Error fetching current user:', error)
    return null
  }
  return user
}
