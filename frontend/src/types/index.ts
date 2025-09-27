// User types
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  display_name: string;
  avatar_url?: string;
  is_active: boolean;
  is_verified: boolean;
  has_google_access: boolean;
  has_hubspot_access: boolean;
  preferences?: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

// Chat types
export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type?: string;
  metadata?: Record<string, any>;
  model_used?: string;
  tokens_used?: number;
  processing_time_ms?: number;
  context_sources?: string[];
  tools_called?: ToolCall[];
  is_streaming: boolean;
  is_complete: boolean;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title?: string;
  context?: Record<string, any>;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
}

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

// API Response types
export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Auth types
export interface LoginRequest {
  email: string;
  password?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Integration types
export interface IntegrationAccount {
  id: string;
  user_id: string;
  service: 'google' | 'hubspot';
  account_id: string;
  account_email?: string;
  account_name?: string;
  is_active: boolean;
  is_connected: boolean;
  has_valid_token: boolean;
  needs_token_refresh: boolean;
  last_sync_at?: string;
  sync_error?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  connected_at: string;
  disconnected_at?: string;
}

// Task types
export interface Task {
  id: string;
  user_id: string;
  task_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  title?: string;
  description?: string;
  input_data: Record<string, any>;
  output_data?: Record<string, any>;
  tool_name?: string;
  tool_parameters?: Record<string, any>;
  tool_result?: Record<string, any>;
  parent_task_id?: string;
  depends_on_task_id?: string;
  scheduled_for?: string;
  priority: number;
  progress_percentage: number;
  current_step?: string;
  total_steps?: number;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

// RAG types
export interface Document {
  id: string;
  user_id: string;
  source: 'gmail' | 'hubspot' | 'calendar';
  source_id: string;
  document_type: 'email' | 'contact' | 'note' | 'event';
  title?: string;
  content: string;
  summary?: string;
  metadata?: Record<string, any>;
  is_processed: boolean;
  processing_error?: string;
  created_at: string;
  updated_at: string;
  source_created_at?: string;
  source_updated_at?: string;
}

export interface ContextItem {
  content: string;
  source: string;
  document_type: string;
  title?: string;
  relevance_score: number;
  chunk_id: string;
  document_id: string;
}

// Form types
export interface ChatMessageForm {
  message: string;
  context?: Record<string, any>;
}

export interface UserUpdateForm {
  first_name?: string;
  last_name?: string;
  full_name?: string;
  avatar_url?: string;
}

export interface UserPreferencesForm {
  preferences: Record<string, any>;
}

// UI types
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

// WebSocket types
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'error' | 'connection';
  data?: any;
  timestamp: string;
}

// Error types
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
  status?: number;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;