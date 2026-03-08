<script lang="ts">
  import { ui, project } from "$lib/stores";
  import { connectionState, websocket } from "$lib/api/websocket";
  import { fly } from "svelte/transition";
  import AnalyticsConsentDialog from "$lib/components/analytics/AnalyticsConsentDialog.svelte";

  let { children } = $props();

  const tabs = ["chat", "memory", "settings"] as const;
  const shortcuts: Record<string, string> = {
    "1": "chat",
    "2": "memory",
    "3": "settings"
  };

  function handleReconnect() {
    websocket.reconnect();
  }

  // Global keyboard shortcuts for navigation (Cmd/Ctrl + 1/2/3)
  $effect(() => {
    function handleGlobalKeydown(e: KeyboardEvent) {
      // Check for Cmd (Mac) or Ctrl (Windows/Linux) modifier
      if ((e.metaKey || e.ctrlKey) && shortcuts[e.key]) {
        e.preventDefault();
        ui.setActiveTab(shortcuts[e.key] as typeof tabs[number]);
      }
    }

    document.addEventListener("keydown", handleGlobalKeydown);
    return () => document.removeEventListener("keydown", handleGlobalKeydown);
  });

  function getConnectionColor(status: string): string {
    switch (status) {
      case "connected":
        return "bg-green-500";
      case "connecting":
      case "reconnecting":
        return "bg-yellow-500 animate-pulse";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  }

  function getConnectionText(status: string): string {
    switch (status) {
      case "connected":
        return "Connected";
      case "connecting":
        return "Connecting...";
      case "reconnecting":
        return "Reconnecting...";
      case "error":
        return "Connection Error";
      default:
        return "Disconnected";
    }
  }

  function handleTabKeydown(e: KeyboardEvent, currentTab: typeof tabs[number]) {
    const currentIndex = tabs.indexOf(currentTab);
    let newIndex = currentIndex;

    if (e.key === "ArrowDown" || e.key === "ArrowRight") {
      e.preventDefault();
      newIndex = (currentIndex + 1) % tabs.length;
    } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
      e.preventDefault();
      newIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    } else if (e.key === "Home") {
      e.preventDefault();
      newIndex = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      newIndex = tabs.length - 1;
    }

    if (newIndex !== currentIndex) {
      ui.setActiveTab(tabs[newIndex]);
      // Focus the new tab button
      setTimeout(() => {
        const tabButtons = document.querySelectorAll('[role="tab"]');
        (tabButtons[newIndex] as HTMLElement)?.focus();
      }, 0);
    }
  }
</script>

<div class="flex h-screen bg-surface-950 text-surface-100">
  <!-- Connection Error Banner -->
  {#if $ui.wsStatus === "error" && $project}
    <div 
      class="fixed top-0 left-0 right-0 z-50 bg-red-900/95 border-b border-red-800 px-4 py-3 shadow-lg"
      in:fly={{ y: -50, duration: 300 }}
    >
      <div class="flex items-center justify-between max-w-7xl mx-auto">
        <div class="flex items-center gap-3">
          <svg class="w-5 h-5 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p class="text-sm font-medium text-red-100">Connection Lost</p>
            <p class="text-xs text-red-300">{$ui.wsError || "Unable to connect to the backend server"}</p>
          </div>
        </div>
        <button
          onclick={handleReconnect}
          aria-label="Retry connection to server"
          class="px-4 py-2 text-sm bg-red-700 hover:bg-red-600 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Retry Connection
        </button>
      </div>
    </div>
  {/if}

  <!-- Sidebar -->
  <aside class="w-64 border-r border-surface-800 flex flex-col" in:fly={{ x: -20, duration: 200 }} role="navigation" aria-label="Main navigation">
    <div class="p-4 border-b border-surface-800">
      <h1 class="text-xl font-bold text-ashwen-400">Ashwen</h1>
      <p class="text-xs text-surface-500 mt-1" aria-live="polite">
        {#if $project}
          {$project.name}
        {:else}
          No project selected
        {/if}
      </p>
    </div>

    <nav class="flex-1 p-2" role="tablist" aria-label="Application tabs">
      <button
        onclick={() => ui.setActiveTab("chat")}
        onkeydown={(e) => handleTabKeydown(e, "chat")}
        role="tab"
        aria-selected={$ui.activeTab === 'chat'}
        aria-controls="tab-panel"
        tabindex={$ui.activeTab === 'chat' ? 0 : -1}
        class="w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between {$ui.activeTab === 'chat' ? 'bg-surface-800 text-white' : 'hover:bg-surface-900'}"
      >
        <span>Group Chat</span>
        <kbd class="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400 font-mono">⌘1</kbd>
      </button>
      <button
        onclick={() => ui.setActiveTab("memory")}
        onkeydown={(e) => handleTabKeydown(e, "memory")}
        role="tab"
        aria-selected={$ui.activeTab === 'memory'}
        aria-controls="tab-panel"
        tabindex={$ui.activeTab === 'memory' ? 0 : -1}
        class="w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between {$ui.activeTab === 'memory' ? 'bg-surface-800 text-white' : 'hover:bg-surface-900'}"
      >
        <span>Memory</span>
        <kbd class="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400 font-mono">⌘2</kbd>
      </button>
      <button
        onclick={() => ui.setActiveTab("settings")}
        onkeydown={(e) => handleTabKeydown(e, "settings")}
        role="tab"
        aria-selected={$ui.activeTab === 'settings'}
        aria-controls="tab-panel"
        tabindex={$ui.activeTab === 'settings' ? 0 : -1}
        class="w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between {$ui.activeTab === 'settings' ? 'bg-surface-800 text-white' : 'hover:bg-surface-900'}"
      >
        <span>Settings</span>
        <kbd class="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400 font-mono">⌘3</kbd>
      </button>
    </nav>

    <div class="p-4 border-t border-surface-800">
      <!-- Connection Status -->
      <div class="space-y-2" role="status" aria-live="polite" aria-label="Connection status">
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full {getConnectionColor($ui.wsStatus)}" aria-hidden="true"></div>
          <span class="text-xs text-surface-400 font-medium">
            {getConnectionText($ui.wsStatus)}
          </span>
        </div>

        <!-- Error Message -->
        {#if $ui.wsError}
          <div class="text-xs text-red-400 bg-red-900/20 p-2 rounded border border-red-800">
            {$ui.wsError}
          </div>
        {/if}

        <!-- Reconnecting Progress -->
        {#if $ui.wsStatus === "reconnecting" && $connectionState.reconnectAttempts > 0}
          <div class="text-xs text-surface-500">
            Attempt {$connectionState.reconnectAttempts}/{$connectionState.maxReconnectAttempts}
          </div>
        {/if}

        <!-- Manual Reconnect Button -->
        {#if $ui.wsStatus === "error" || $ui.wsStatus === "disconnected"}
          <button
            onclick={handleReconnect}
            aria-label="Reconnect to server"
            class="w-full mt-2 px-3 py-1.5 text-xs bg-ashwen-600 hover:bg-ashwen-700 text-white rounded transition-colors"
          >
            Reconnect
          </button>
        {/if}
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <main class="flex-1 flex flex-col overflow-hidden" id="tab-panel" role="tabpanel" aria-label="Main content">
    {@render children()}
  </main>

  <!-- Analytics Consent Dialog -->
  <AnalyticsConsentDialog />
</div>
