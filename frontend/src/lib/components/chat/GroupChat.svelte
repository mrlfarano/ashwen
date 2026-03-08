<script lang="ts">
  import { get } from "svelte/store";
  import { messages, agentsById, project, ui } from "$lib/stores";
  import { websocket } from "$lib/api/websocket";
  import { streamBuffers } from "$lib/api/websocket";
  import Message from "./Message.svelte";

  let inputText = $state("");
  let containerEl: HTMLDivElement;

  // Derived values for DM mode
  const selectedAgent = $derived($agentsById[$ui.selectedAgentId || ""]);
  const isDmMode = $derived($ui.dmMode && selectedAgent);

  $effect(() => {
    if ($messages.length > 0 && containerEl) {
      containerEl.scrollTop = containerEl.scrollHeight;
    }
  });

  function sendMessage() {
    if (!inputText.trim()) return;

    const content = inputText.trim();
    const currentDmMode = get(ui).dmMode;
    const selectedAgentId = get(ui).selectedAgentId;

    inputText = "";

    messages.add({
      id: crypto.randomUUID(),
      project_id: get(project)?.id || "",
      agent_id: null,
      role: "user",
      content,
      message_type: currentDmMode && selectedAgentId ? "dm" : "chat",
      confidence: null,
      tokens_used: null,
      created_at: new Date().toISOString(),
    });

    websocket.send("user:message", {
      content,
      selected_agent_id: selectedAgentId,
      is_dm: currentDmMode && !!selectedAgentId,
    });
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function toggleDmMode() {
    if ($ui.selectedAgentId) {
      ui.toggleDmMode();
    }
  }
</script>

<div class="flex-1 flex flex-col" role="region" aria-label="Group chat">
  <!-- Messages -->
  <div
    bind:this={containerEl}
    class="flex-1 overflow-y-auto p-4 space-y-4"
    role="log"
    aria-label="Chat messages"
    aria-live="polite"
  >
    {#each $messages as msg}
      <Message {msg} agent={$agentsById[msg.agent_id || ""]} />
    {/each}

    {#each $streamBuffers as [agentId, buffer]}
      <article class="flex gap-3 p-3 rounded-lg bg-surface-900" aria-label="{$agentsById[agentId]?.name || 'Agent'} is typing">
        <div class="w-8 h-8 rounded-full bg-ashwen-700 flex items-center justify-center text-sm" aria-hidden="true">
          {$agentsById[agentId]?.name?.[0] || "?"}
        </div>
        <div class="flex-1">
          <div class="text-sm font-medium text-ashwen-400">
            {$agentsById[agentId]?.name || "Agent"}
            <span class="text-surface-500 ml-2" aria-label="streaming">streaming...</span>
          </div>
          <div class="mt-1 text-surface-200 whitespace-pre-wrap">{buffer.content}</div>
        </div>
      </article>
    {/each}

    {#if $messages.length === 0}
      <div class="flex-1 flex items-center justify-center text-surface-500">
        <div class="text-center">
          <p class="text-lg mb-2">Start a conversation</p>
          <p class="text-sm">Your agent team is ready to help</p>
        </div>
      </div>
    {/if}
  </div>

  <!-- DM Mode Indicator Bar -->
  {#if isDmMode}
    <div class="px-4 py-2 bg-ashwen-900/50 border-y border-ashwen-700/50 flex items-center justify-between" role="status" aria-live="polite">
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-ashwen-700/50 text-ashwen-300 text-sm font-medium" aria-hidden="true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          DM
        </span>
        <span class="text-surface-300 text-sm">
          Direct message to <span class="font-medium text-ashwen-300">{selectedAgent?.name}</span>
        </span>
      </div>
      <button
        onclick={() => ui.setDmMode(false)}
        aria-label="Switch to group chat"
        class="text-surface-400 hover:text-surface-200 text-sm px-2 py-1 rounded hover:bg-surface-800 transition-colors focus:outline-none focus:ring-2 focus:ring-ashwen-500"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  {/if}

  <!-- Input -->
  <div class="border-t border-surface-800 p-4">
    <form class="flex gap-2" onsubmit={(e) => { e.preventDefault(); sendMessage(); }}>
      <!-- DM Toggle Button -->
      {#if $ui.selectedAgentId}
        <button
          type="button"
          onclick={toggleDmMode}
          aria-pressed={$ui.dmMode}
          aria-label={$ui.dmMode ? 'Switch to group chat' : 'Switch to direct message mode'}
          class="px-3 py-2 rounded-lg transition-colors {$ui.dmMode ? 'bg-ashwen-700 text-ashwen-100' : 'bg-surface-800 text-surface-400 hover:bg-surface-700 hover:text-surface-200'} focus:outline-none focus:ring-2 focus:ring-ashwen-500"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      {/if}

      <label class="sr-only" for="message-input">Message</label>
      <textarea
        id="message-input"
        bind:value={inputText}
        onkeydown={handleKeydown}
        placeholder={isDmMode ? `Message ${selectedAgent?.name} directly...` : "Type a message..."}
        aria-label="Message input"
        class="flex-1 bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-ashwen-500"
        rows="1"
      ></textarea>
      <button
        type="submit"
        disabled={!inputText.trim() || $ui.wsStatus === "connecting"}
        aria-label="Send message"
        class="px-4 py-2 bg-ashwen-600 hover:bg-ashwen-500 disabled:bg-surface-800 disabled:text-surface-500 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-ashwen-500 focus:ring-offset-2 focus:ring-offset-surface-950"
      >
        Send
      </button>
    </form>
  </div>
</div>
