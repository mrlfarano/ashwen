import { writable, get } from "svelte/store";
import { messages, ui, agents, project } from "$lib/stores";
import type {
  Message,
  StreamBuffer,
  ConnectionState,
  WSMessage,
  WSConnectionStatus,
} from "./types";

const WS_URL =
  (typeof window !== "undefined" ? window.ashwen?.backend?.wsUrl : undefined) ||
  import.meta.env.VITE_WS_URL ||
  "ws://localhost:8000/ws";

// Configuration constants
const WS_CONFIG = {
  maxReconnectAttempts: 10,
  initialReconnectDelay: 1000,
  maxReconnectDelay: 30000,
  heartbeatInterval: 30000, // 30 seconds
  heartbeatTimeout: 10000, // 10 seconds to wait for pong
  maxQueueSize: 100,
  maxMessageRetries: 3,
  connectionTimeout: 15000, // 15 seconds to establish connection
} as const;

interface QueuedMessage {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: number;
  retries: number;
}

interface HeartbeatState {
  lastSent: number;
  lastReceived: number;
  pendingPong: boolean;
  intervalId: ReturnType<typeof setInterval> | null;
  timeoutId: ReturnType<typeof setTimeout> | null;
}

export const streamBuffers = writable<StreamBuffer>(new Map());
export const connectionState = writable<ConnectionState>({
  status: "disconnected",
  error: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: WS_CONFIG.maxReconnectAttempts,
});

function createWebSocketStore() {
  const { subscribe, set } = writable<WebSocket | null>(null);

  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let connectionTimeoutId: ReturnType<typeof setTimeout> | null = null;
  let currentProjectId: string | null = null;
  let manualDisconnect = false;
  let messageQueue: QueuedMessage[] = [];
  let heartbeat: HeartbeatState = {
    lastSent: 0,
    lastReceived: 0,
    pendingPong: false,
    intervalId: null,
    timeoutId: null,
  };

  function updateConnectionState(partial: Partial<ConnectionState>) {
    connectionState.update((state) => ({ ...state, ...partial }));
    
    // Sync with UI store
    if (partial.status) {
      ui.setWsStatus(partial.status, partial.error);
    } else if (partial.error !== undefined) {
      const currentState = get(connectionState);
      ui.setWsStatus(currentState.status, partial.error);
    }
  }

  function clearTimers() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
    if (connectionTimeoutId) {
      clearTimeout(connectionTimeoutId);
      connectionTimeoutId = null;
    }
    if (heartbeat.intervalId) {
      clearInterval(heartbeat.intervalId);
      heartbeat.intervalId = null;
    }
    if (heartbeat.timeoutId) {
      clearTimeout(heartbeat.timeoutId);
      heartbeat.timeoutId = null;
    }
  }

  function startHeartbeat() {
    // Clear any existing heartbeat
    if (heartbeat.intervalId) {
      clearInterval(heartbeat.intervalId);
    }
    
    heartbeat.lastReceived = Date.now();
    heartbeat.pendingPong = false;
    
    heartbeat.intervalId = setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
      }
      
      // Check if we've been waiting too long for a pong
      if (heartbeat.pendingPong) {
        const elapsed = Date.now() - heartbeat.lastSent;
        if (elapsed > WS_CONFIG.heartbeatTimeout) {
          console.warn("[WS] Heartbeat timeout - connection may be dead");
          // Force reconnection
          ws.close(4000, "Heartbeat timeout");
          return;
        }
      }
      
      // Send ping
      try {
        ws.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
        heartbeat.lastSent = Date.now();
        heartbeat.pendingPong = true;
      } catch (err) {
        console.error("[WS] Failed to send heartbeat:", err);
      }
    }, WS_CONFIG.heartbeatInterval);
  }

  function handlePong() {
    heartbeat.lastReceived = Date.now();
    heartbeat.pendingPong = false;
  }

  function calculateReconnectDelay(): number {
    // Exponential backoff with jitter
    const baseDelay = WS_CONFIG.initialReconnectDelay;
    const maxDelay = WS_CONFIG.maxReconnectDelay;
    const exponentialDelay = baseDelay * Math.pow(2, reconnectAttempts);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    return Math.min(exponentialDelay + jitter, maxDelay);
  }

  function scheduleReconnect() {
    if (!currentProjectId || manualDisconnect) {
      return;
    }
    
    if (reconnectAttempts >= WS_CONFIG.maxReconnectAttempts) {
      updateConnectionState({
        status: "error",
        error: `Maximum reconnection attempts (${WS_CONFIG.maxReconnectAttempts}) reached. Click reconnect to try again.`,
      });
      return;
    }
    
    reconnectAttempts++;
    const delay = calculateReconnectDelay();
    
    updateConnectionState({
      status: "reconnecting",
      reconnectAttempts,
      error: `Connection lost. Reconnecting in ${Math.round(delay / 1000)}s (${reconnectAttempts}/${WS_CONFIG.maxReconnectAttempts})...`,
    });
    
    console.log(`[WS] Scheduling reconnect attempt ${reconnectAttempts} in ${delay}ms`);
    
    reconnectTimeout = setTimeout(() => {
      if (currentProjectId && !manualDisconnect) {
        connect(currentProjectId);
      }
    }, delay);
  }

  function connect(projectId: string) {
    // Clean up existing connection
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      if (currentProjectId === projectId) {
        console.log("[WS] Already connected to project:", projectId);
        return;
      }
      manualDisconnect = true;
      ws.close(1000, "Switching projects");
    }

    clearTimers();
    manualDisconnect = false;
    currentProjectId = projectId;
    updateConnectionState({ status: "connecting", error: null });

    // Connection timeout
    connectionTimeoutId = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.CONNECTING) {
        console.warn("[WS] Connection timeout");
        ws.close(4001, "Connection timeout");
      }
    }, WS_CONFIG.connectionTimeout);

    try {
      const socket = new WebSocket(`${WS_URL}/${projectId}`);
      ws = socket;

      socket.onopen = () => {
        if (socket !== ws) return;

        console.log("[WS] Connected to project:", projectId);
        clearTimers();
        
        updateConnectionState({
          status: "connected",
          error: null,
          reconnectAttempts: 0,
        });
        reconnectAttempts = 0;

        // Start heartbeat for connection health monitoring
        startHeartbeat();
        
        // Flush message queue
        flushMessageQueue();
      };

      socket.onclose = (event) => {
        if (socket !== ws) return;

        console.log("[WS] Disconnected:", event.code, event.reason);
        clearTimers();
        updateConnectionState({ status: "disconnected" });

        if (manualDisconnect) {
          manualDisconnect = false;
          return;
        }

        // Handle specific close codes
        switch (event.code) {
          case 4000:
            console.warn("[WS] Heartbeat timeout - scheduling reconnect");
            break;
          case 4001:
            console.warn("[WS] Connection timeout - scheduling reconnect");
            break;
          case 1006:
            // Abnormal closure - likely network issue
            console.warn("[WS] Abnormal closure - network issue likely");
            break;
          case 1001:
            // Going away - server shutting down or page navigation
            console.log("[WS] Server going away");
            break;
        }

        scheduleReconnect();
      };

      socket.onerror = (err) => {
        if (socket !== ws) return;

        console.error("[WS] Error:", err);
        
        // Don't update state here - let onclose handle it
        // This prevents duplicate error messages
      };

      socket.onmessage = (event) => {
        if (socket !== ws) return;

        try {
          const data: WSMessage = JSON.parse(event.data);
          
          // Handle pong responses
          if (data.type === "pong") {
            handlePong();
            return;
          }
          
          handleMessage(data, streamBuffers);
        } catch (e) {
          console.error("[WS] Parse error:", e);
          updateConnectionState({
            error: "Failed to parse server message",
          });
        }
      };

      set(socket);
    } catch (err) {
      console.error("[WS] Connection error:", err);
      clearTimers();
      updateConnectionState({
        status: "error",
        error: `Failed to create WebSocket connection: ${err}`,
      });
      scheduleReconnect();
    }
  }

  function disconnect() {
    console.log("[WS] Manual disconnect");
    manualDisconnect = true;
    clearTimers();
    currentProjectId = null;
    reconnectAttempts = 0;
    ws?.close(1000, "Client disconnect");
    ws = null;
    streamBuffers.set(new Map());
    messageQueue = [];
    heartbeat = {
      lastSent: 0,
      lastReceived: 0,
      pendingPong: false,
      intervalId: null,
      timeoutId: null,
    };
    updateConnectionState({
      status: "disconnected",
      error: null,
      reconnectAttempts: 0,
    });
    set(null);
  }

  function reconnect() {
    const projectId = currentProjectId;

    if (!projectId) {
      updateConnectionState({
        error: "No project to reconnect to",
      });
      return;
    }

    // Reset reconnect attempts for manual reconnect
    reconnectAttempts = 0;
    disconnect();
    
    // Small delay before reconnecting
    setTimeout(() => {
      connect(projectId!);
    }, 100);
  }

  function flushMessageQueue() {
    if (messageQueue.length === 0) return;

    console.log(`[WS] Flushing ${messageQueue.length} queued messages`);
    const failedMessages: QueuedMessage[] = [];

    for (const msg of messageQueue) {
      if (msg.retries >= WS_CONFIG.maxMessageRetries) {
        console.warn(`[WS] Dropping message after ${WS_CONFIG.maxMessageRetries} retries:`, msg.type);
        continue;
      }

      try {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: msg.type, ...msg.payload }));
        } else {
          msg.retries++;
          failedMessages.push(msg);
        }
      } catch (err) {
        console.error("[WS] Failed to send queued message:", err);
        msg.retries++;
        failedMessages.push(msg);
      }
    }

    messageQueue = failedMessages.slice(-WS_CONFIG.maxQueueSize);
    
    if (messageQueue.length > 0) {
      console.log(`[WS] ${messageQueue.length} messages still queued`);
    }
  }

  function send(type: string, payload: Record<string, unknown>) {
    const queuedMsg: QueuedMessage = {
      id: crypto.randomUUID(),
      type,
      payload,
      timestamp: Date.now(),
      retries: 0,
    };

    if (ws?.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type, ...payload }));
      } catch (err) {
        console.error("[WS] Send error:", err);
        // Queue for retry
        messageQueue.push(queuedMsg);
        if (messageQueue.length > WS_CONFIG.maxQueueSize) {
          messageQueue.shift();
        }
      }
    } else {
      // Queue message for later
      const state = ws?.readyState;
      const stateStr = state === WebSocket.CONNECTING ? "connecting" :
                       state === WebSocket.CLOSING ? "closing" :
                       state === WebSocket.CLOSED ? "closed" : "not created";
      console.log(`[WS] Queuing message (connection ${stateStr}):`, type);
      
      messageQueue.push(queuedMsg);
      if (messageQueue.length > WS_CONFIG.maxQueueSize) {
        messageQueue.shift();
      }

      // If disconnected and not reconnecting, try to connect
      if (!ws || ws.readyState === WebSocket.CLOSED) {
        const currentState = get(connectionState);
        if (currentState.status !== "reconnecting" && currentProjectId) {
          console.log("[WS] Attempting to restore connection");
          connect(currentProjectId);
        }
      }
    }
  }

  function clearQueue() {
    messageQueue = [];
  }

  function getConnectionHealth(): { latency: number | null; healthy: boolean } {
    if (!heartbeat.lastSent || !heartbeat.lastReceived) {
      return { latency: null, healthy: false };
    }
    
    const latency = heartbeat.lastReceived - heartbeat.lastSent;
    const healthy = !heartbeat.pendingPong && latency < WS_CONFIG.heartbeatTimeout;
    
    return { latency, healthy };
  }

  return { 
    subscribe, 
    connect, 
    disconnect, 
    reconnect, 
    send, 
    clearQueue,
    getConnectionHealth,
  };
}

function handleMessage(data: WSMessage, streamBuffers: { update: (fn: (m: StreamBuffer) => StreamBuffer) => void }) {
  switch (data.type) {
    case "agent:message":
      const msg: Message = {
        id: crypto.randomUUID(),
        project_id: get(project)?.id || "",
        agent_id: data.agent_id,
        role: "assistant",
        content: data.content,
        message_type: data.message_type ?? "chat",
        confidence: data.confidence ?? null,
        tokens_used: null,
        created_at: new Date().toISOString(),
      };
      messages.add(msg);
      
      streamBuffers.update((buffers) => {
        buffers.delete(data.agent_id);
        return buffers;
      });
      break;

    case "agent:stream":
      streamBuffers.update((buffers) => {
        const existing = buffers.get(data.agent_id) || { content: "", agent_id: data.agent_id };
        buffers.set(data.agent_id, {
          ...existing,
          content: existing.content + data.chunk,
        });
        return buffers;
      });
      break;

    case "agent:status":
      agents.update(data.agent_id, { status: data.status });
      break;

    case "proactive:triggered":
      console.log(`[Proactive] ${data.agent_id}: ${data.reason}`);
      break;

    case "memory:update":
      console.log("[Memory] Updated:", data.entry);
      break;

    case "system:error":
      messages.add({
        id: crypto.randomUUID(),
        project_id: get(project)?.id || "",
        agent_id: null,
        role: "system",
        content: data.detail,
        message_type: "system",
        confidence: null,
        tokens_used: null,
        created_at: new Date().toISOString(),
      });
      break;
      
    case "pong":
      // Handled in onmessage directly
      break;
  }
}

export const websocket = createWebSocketStore();
