import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  CredentialStatus,
  CredentialStored,
  DeleteResponse,
  InitializeAgentsResponse,
  MemoryCreate,
  MemoryEntry,
  Message,
  Project,
  ProjectCreate,
} from "./types";

const API_BASE =
  (typeof window !== "undefined" ? window.ashwen?.backend?.httpUrl : undefined) ||
  import.meta.env.VITE_API_BASE ||
  "http://localhost:8000";

function parseJsonField<T>(value: unknown, fallback: T): T {
  if (typeof value !== "string") return (value as T) ?? fallback;

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function normalizeItem(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(normalizeItem);
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  const item = { ...(value as Record<string, unknown>) };

  if ("linked_projects" in item) {
    item.linked_projects = parseJsonField(item.linked_projects, [] as string[]);
  }

  if ("llm_config" in item) {
    item.llm_config = parseJsonField(item.llm_config, {} as Record<string, unknown>);
  }

  if ("entry_metadata" in item && !("metadata" in item)) {
    item.metadata = parseJsonField(item.entry_metadata, {} as Record<string, unknown>);
  }

  if ("metadata" in item) {
    item.metadata = parseJsonField(item.metadata, {} as Record<string, unknown>);
  }

  return item;
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error) return error;
  return fallback;
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const data = await response.json();
  return normalizeItem(data) as T;
}

// ============================================================================
// Projects API
// ============================================================================

export const projectsApi = {
  list: () => api<Project[]>("/projects"),
  get: (id: string) => api<Project>(`/projects/${id}`),
  getMessages: (id: string) => api<Message[]>(`/projects/${id}/messages`),
  create: (payload: ProjectCreate) =>
    api<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  delete: (id: string) => api<DeleteResponse>(`/projects/${id}`, { method: "DELETE" }),
};

// ============================================================================
// Agents API
// ============================================================================

export const agentsApi = {
  list: (projectId: string) => api<Agent[]>(`/agents/project/${projectId}`),
  get: (id: string) => api<Agent>(`/agents/${id}`),
  create: (projectId: string, payload: AgentCreate) =>
    api<Agent>(`/agents/project/${projectId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, data: AgentUpdate) =>
    api<Agent>(`/agents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  initialize: (projectId: string) =>
    api<InitializeAgentsResponse>(`/agents/project/${projectId}/initialize`, { method: "POST" }),
  delete: (id: string) => api<DeleteResponse>(`/agents/${id}`, { method: "DELETE" }),
};

// ============================================================================
// Memory API
// ============================================================================

export const memoryApi = {
  list: (projectId: string, type?: string) => {
    const params = type ? `?memory_type=${type}` : "";
    return api<MemoryEntry[]>(`/memory/project/${projectId}${params}`);
  },
  get: (id: string) => api<MemoryEntry>(`/memory/${id}`),
  create: (projectId: string, payload: MemoryCreate) =>
    api<MemoryEntry>(`/memory/project/${projectId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: Partial<MemoryCreate>) =>
    api<MemoryEntry>(`/memory/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  search: (projectId: string, query: string, type?: string) => {
    const params = new URLSearchParams({ q: query });
    if (type) params.append("memory_type", type);
    return api<MemoryEntry[]>(`/memory/project/${projectId}/search?${params}`);
  },
  delete: (id: string) => api<DeleteResponse>(`/memory/${id}`, { method: "DELETE" }),
};

// ============================================================================
// Credentials API
// ============================================================================

export const credentialsApi = {
  list: () => api<string[]>("/credentials"),
  has: (provider: string) => api<CredentialStatus>(`/credentials/${provider}`),
  set: (provider: string, apiKey: string) =>
    api<CredentialStored>(`/credentials/${provider}`, {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    }),
  delete: (provider: string) => api<DeleteResponse>(`/credentials/${provider}`, { method: "DELETE" }),
};
