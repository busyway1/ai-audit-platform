/**
 * Supabase Database Type Definitions
 *
 * This file contains TypeScript type definitions matching the database schema
 * from the POC plan. These are placeholder types based on the schema specification
 * and will be regenerated using `npx supabase gen types` once Window 3 deploys
 * the actual schema.
 *
 * @module types/supabase
 */

// JSON type for JSONB fields
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

// Enum types for status fields (aligned with actual schema)
export type AuditProjectStatus = 'Planning' | 'Execution' | 'Review' | 'Completed'
export type AuditTaskStatus = 'Pending' | 'In-Progress' | 'Review-Required' | 'Completed' | 'Failed'
export type EGARiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'
export type EGAStatus = 'Not-Started' | 'In-Progress' | 'Completed'
export type MessageType = 'instruction' | 'response' | 'tool-use' | 'human-feedback'
export type ArtifactType = 'workpaper' | 'excel' | 'voucher' | 'memo' | 'report'
export type StandardType = 'K-IFRS' | 'K-GAAS'
export type HITLRequestStatus = 'pending' | 'approved' | 'rejected' | 'expired'
export type HITLRequestType = 'approval' | 'clarification' | 'escalation' | 'review'

export interface Database {
  public: {
    Tables: {
      audit_projects: {
        Row: {
          id: string
          client_name: string
          fiscal_year: number
          overall_materiality: number | null
          status: AuditProjectStatus
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          client_name: string
          fiscal_year: number
          overall_materiality?: number | null
          status?: AuditProjectStatus
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          client_name?: string
          fiscal_year?: number
          overall_materiality?: number | null
          status?: AuditProjectStatus
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
      audit_tasks: {
        Row: {
          id: string
          project_id: string
          thread_id: string
          category: string
          status: AuditTaskStatus
          risk_score: number | null
          assignees: Json
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          project_id: string
          thread_id: string
          category: string
          status?: AuditTaskStatus
          risk_score?: number | null
          assignees?: Json
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          thread_id?: string
          category?: string
          status?: AuditTaskStatus
          risk_score?: number | null
          assignees?: Json
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
      agent_messages: {
        Row: {
          id: string
          task_id: string
          agent_role: string
          content: string
          message_type: MessageType
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          task_id: string
          agent_role: string
          content: string
          message_type?: MessageType
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          task_id?: string
          agent_role?: string
          content?: string
          message_type?: MessageType
          metadata?: Json
          created_at?: string
        }
      }
      audit_artifacts: {
        Row: {
          id: string
          task_id: string
          artifact_type: ArtifactType
          file_path: string | null
          content: string | null
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          task_id: string
          artifact_type?: ArtifactType
          file_path?: string | null
          content?: string | null
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          task_id?: string
          artifact_type?: ArtifactType
          file_path?: string | null
          content?: string | null
          metadata?: Json
          created_at?: string
        }
      }
      audit_standards: {
        Row: {
          id: string
          parent_id: string | null
          standard_type: StandardType
          section_number: string | null
          title: string
          content: string
          embedding: string | null // vector type represented as string
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          parent_id?: string | null
          standard_type: StandardType
          section_number?: string | null
          title: string
          content: string
          embedding?: string | null
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          parent_id?: string | null
          standard_type?: StandardType
          section_number?: string | null
          title?: string
          content?: string
          embedding?: string | null
          metadata?: Json
          created_at?: string
        }
      }
      audit_egas: {
        Row: {
          id: string
          project_id: string
          name: string
          description: string | null
          risk_level: EGARiskLevel
          status: EGAStatus
          progress: number
          total_tasks: number
          completed_tasks: number
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          project_id: string
          name: string
          description?: string | null
          risk_level?: EGARiskLevel
          status?: EGAStatus
          progress?: number
          total_tasks?: number
          completed_tasks?: number
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          name?: string
          description?: string | null
          risk_level?: EGARiskLevel
          status?: EGAStatus
          progress?: number
          total_tasks?: number
          completed_tasks?: number
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
      hitl_requests: {
        Row: {
          id: string
          task_id: string
          project_id: string
          request_type: HITLRequestType
          urgency_score: number
          title: string
          context: string
          options: Json
          status: HITLRequestStatus
          response: string | null
          responded_by: string | null
          responded_at: string | null
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          task_id: string
          project_id: string
          request_type?: HITLRequestType
          urgency_score?: number
          title: string
          context: string
          options?: Json
          status?: HITLRequestStatus
          response?: string | null
          responded_by?: string | null
          responded_at?: string | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          task_id?: string
          project_id?: string
          request_type?: HITLRequestType
          urgency_score?: number
          title?: string
          context?: string
          options?: Json
          status?: HITLRequestStatus
          response?: string | null
          responded_by?: string | null
          responded_at?: string | null
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
      }
    }
  }
}

// Helper types for common database operations
export type Tables<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Row']
export type Insertable<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Insert']
export type Updatable<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Update']

// Specific table type aliases for convenience
export type AuditProject = Tables<'audit_projects'>
export type AuditTask = Tables<'audit_tasks'>
export type AgentMessage = Tables<'agent_messages'>
export type AuditArtifact = Tables<'audit_artifacts'>
export type AuditStandard = Tables<'audit_standards'>
export type AuditEGA = Tables<'audit_egas'>
export type HITLRequest = Tables<'hitl_requests'>

// Insertable type aliases
export type AuditProjectInsert = Insertable<'audit_projects'>
export type AuditTaskInsert = Insertable<'audit_tasks'>
export type AgentMessageInsert = Insertable<'agent_messages'>
export type AuditArtifactInsert = Insertable<'audit_artifacts'>
export type AuditStandardInsert = Insertable<'audit_standards'>
export type AuditEGAInsert = Insertable<'audit_egas'>
export type HITLRequestInsert = Insertable<'hitl_requests'>

// Updatable type aliases
export type AuditProjectUpdate = Updatable<'audit_projects'>
export type AuditTaskUpdate = Updatable<'audit_tasks'>
export type AgentMessageUpdate = Updatable<'agent_messages'>
export type AuditArtifactUpdate = Updatable<'audit_artifacts'>
export type AuditStandardUpdate = Updatable<'audit_standards'>
export type AuditEGAUpdate = Updatable<'audit_egas'>
export type HITLRequestUpdate = Updatable<'hitl_requests'>
