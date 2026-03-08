/**
 * API Types - TypeScript interfaces matching backend models and schemas
 */

// ============================================================================
// Project Types
// ============================================================================

export interface Project {
  id: string;
  name: string;
  path: string;
  description: string | null;
  linked_projects: string[];
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string | null;
}

// ============================================================================
// Agent Types
// ============================================================================

export type AgentStatus = "idle" | "thinking" | "active";

export interface Agent {
  id: string;
  project_id: string;
  name: string;
  persona: string;
  system_prompt: string;
  llm_provider: string;
  llm_model: string;
  llm_config: Record<string, unknown>;
  proactivity_enabled: boolean;
  confidence_threshold: number;
  status: AgentStatus;
  created_at: string;
}

export interface AgentCreate {
  name: string;
  persona: string;
  system_prompt: string;
  llm_provider?: string;
  llm_model?: string;
  llm_config?: Record<string, unknown>;
  proactivity_enabled?: boolean;
  confidence_threshold?: number;
}

export interface AgentUpdate {
  name?: string;
  persona?: string;
  system_prompt?: string;
  llm_provider?: string;
  llm_model?: string;
  llm_config?: Record<string, unknown>;
  proactivity_enabled?: boolean;
  confidence_threshold?: number;
}

// ============================================================================
// Message Types
// ============================================================================

export type MessageRole = "user" | "assistant" | "system";
export type MessageType = "chat" | "dm" | "system";

export interface Message {
  id: string;
  project_id: string;
  agent_id: string | null;
  role: MessageRole;
  content: string;
  message_type: MessageType;
  confidence: number | null;
  tokens_used: number | null;
  created_at: string;
}

// ============================================================================
// Memory Types
// ============================================================================

export interface MemoryEntry {
  id: string;
  project_id: string;
  memory_type: string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
  file_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  memory_type: string;
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface MemoryUpdate {
  title?: string;
  content?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Credential Types
// ============================================================================

export interface CredentialSet {
  api_key: string;
}

export interface CredentialStatus {
  provider: string;
  configured: boolean;
}

export interface CredentialStored {
  provider: string;
  stored: boolean;
  action?: string | null;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface DeleteResponse {
  deleted: boolean;
  project_id?: string | null;
  agent_id?: string | null;
  memory_id?: string | null;
}

export interface InitializeAgentsResponse {
  initialized: number;
  project_id: string;
  agents: string[];
}

// ============================================================================
// WebSocket Types
// ============================================================================

export type WSConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting" | "error";

export interface WSMessageAgentMessage {
  type: "agent:message";
  agent_id: string;
  content: string;
  confidence?: number;
  message_type?: MessageType;
}

export interface WSMessageAgentStream {
  type: "agent:stream";
  agent_id: string;
  chunk: string;
}

export interface WSMessageAgentStatus {
  type: "agent:status";
  agent_id: string;
  status: AgentStatus;
}

export interface WSMessageProactiveTriggered {
  type: "proactive:triggered";
  agent_id: string;
  reason: string;
}

export interface WSMessageMemoryUpdate {
  type: "memory:update";
  entry: MemoryEntry;
}

export interface WSMessageSystemError {
  type: "system:error";
  detail: string;
}

export type WSMessage =
  | WSMessageAgentMessage
  | WSMessageAgentStream
  | WSMessageAgentStatus
  | WSMessageProactiveTriggered
  | WSMessageMemoryUpdate
  | WSMessageSystemError;

export interface StreamBufferEntry {
  content: string;
  agent_id: string;
}

export type StreamBuffer = Map<string, StreamBufferEntry>;

export interface ConnectionState {
  status: WSConnectionStatus;
  error: string | null;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
}

// ============================================================================
// UI State Types
// ============================================================================

export type UITab = "chat" | "memory" | "settings";

export interface UIState {
  sidebarOpen: boolean;
  activeTab: UITab;
  selectedAgentId: string | null;
  dmMode: boolean;
  wsConnected: boolean;
  wsStatus: WSConnectionStatus;
  wsError: string | null;
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface AnalyticsConsent {
  crashReporting: boolean;
  productAnalytics: boolean;
  hasPrompted: boolean;
}

export interface AnalyticsConsentOptions {
  crashReporting: boolean;
  productAnalytics: boolean;
}

// Window API types
declare global {
  interface Window {
    ashwen?: {
      backend?: {
        httpUrl: string;
        wsUrl: string;
        healthCheck: () => Promise<{ ok: boolean; status?: string; error?: string }>;
      };
      app?: {
        version: string;
        platform: string;
        arch: string;
        isPackaged: boolean;
        getUserDataPath: () => Promise<string>;
        getVersionInfo: () => { version: string; name: string; electron: string; chrome: string; node: string };
      };
      analytics?: {
        getConsent: () => Promise<AnalyticsConsent>;
        setConsent: (options: AnalyticsConsentOptions) => Promise<void>;
        shouldPrompt: () => Promise<boolean>;
        markPrompted: () => Promise<void>;
        trackEvent: (eventName: string, properties?: Record<string, unknown>) => Promise<void>;
      };
      files?: {
        openFile: (options?: Record<string, unknown>) => Promise<string | null>;
        saveFile: (options?: Record<string, unknown>) => Promise<string | null>;
      };
      shell?: {
        openExternal: (url: string) => Promise<void>;
      };
      clipboard?: {
        writeText: (text: string) => Promise<void>;
        readText: () => Promise<string>;
      };
      log?: {
        info: (message: string) => Promise<void>;
        warn: (message: string) => Promise<void>;
        error: (message: string) => Promise<void>;
      };
      window?: {
        minimize: () => void;
        toggleMaximize: () => void;
        close: () => void;
        isMaximized: () => Promise<boolean>;
      };
      updates?: {
        checkForUpdates: () => Promise<{ available: boolean; version?: string; error?: string }>;
        installUpdate: () => Promise<void>;
        onEvent: (event: string, callback: (data: unknown) => void) => () => void;
      };
    };
  }
}

export {};
