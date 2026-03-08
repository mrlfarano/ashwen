import { writable, derived } from "svelte/store";
import type {
  Agent,
  AgentStatus,
  Message,
  MessageType,
  Project,
  StreamBuffer,
  UIState,
  UITab,
  WSConnectionStatus,
} from "$lib/api/types";

// Re-export types for convenience
export type {
  Agent,
  AgentStatus,
  Message,
  MessageType,
  Project,
  StreamBuffer,
  UIState,
  UITab,
  WSConnectionStatus,
};

function createProjectStore() {
  const { subscribe, set, update } = writable<Project | null>(null);
  return {
    subscribe,
    set,
    clear: () => set(null),
  };
}

function createAgentsStore() {
  const { subscribe, set, update } = writable<Agent[]>([]);
  return {
    subscribe,
    set,
    add: (agent: Agent) => update((agents) => [...agents, agent]),
    update: (id: string, data: Partial<Agent>) =>
      update((agents) => agents.map((a) => (a.id === id ? { ...a, ...data } : a))),
    remove: (id: string) => update((agents) => agents.filter((a) => a.id !== id)),
    clear: () => set([]),
  };
}

function createMessagesStore() {
  const { subscribe, set, update } = writable<Message[]>([]);
  return {
    subscribe,
    set,
    add: (message: Message) => update((messages) => [...messages, message]),
    prepend: (message: Message) => update((messages) => [message, ...messages]),
    clear: () => set([]),
  };
}

function createUIStore() {
  const initialState: UIState = {
    sidebarOpen: true,
    activeTab: "chat",
    selectedAgentId: null,
    dmMode: false,
    wsConnected: false,
    wsStatus: "disconnected",
    wsError: null,
  };

  const { subscribe, set, update } = writable<UIState>(initialState);
  return {
    subscribe,
    toggleSidebar: () => update((s) => ({ ...s, sidebarOpen: !s.sidebarOpen })),
    setActiveTab: (tab: UITab) => update((s) => ({ ...s, activeTab: tab })),
    selectAgent: (id: string | null) => update((s) => ({ ...s, selectedAgentId: id })),
    clearSelection: () => update((s) => ({ ...s, selectedAgentId: null, dmMode: false })),
    setDmMode: (enabled: boolean) => update((s) => ({ ...s, dmMode: enabled })),
    toggleDmMode: () => update((s) => ({ ...s, dmMode: !s.dmMode })),
    setWsConnected: (connected: boolean) => update((s) => ({ ...s, wsConnected: connected })),
    setWsStatus: (status: WSConnectionStatus, error?: string | null) =>
      update((s) => ({ ...s, wsStatus: status, wsConnected: status === "connected", wsError: error || null })),
    reset: () => set(initialState),
  };
}

export const project = createProjectStore();
export const agents = createAgentsStore();
export const messages = createMessagesStore();
export const ui = createUIStore();

export const activeAgents = derived(agents, ($agents) =>
  $agents.filter((a) => a.status !== "idle")
);

export const agentsById = derived(agents, ($agents) =>
  Object.fromEntries($agents.map((a) => [a.id, a]))
);
