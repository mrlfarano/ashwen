<script lang="ts">
  import type { Agent, Message } from "$lib/stores";

  interface Props {
    msg: Message;
    agent: Agent | undefined;
  }

  let { msg, agent }: Props = $props();

  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";
  const isDm = msg.message_type === "dm";

  function getRoleLabel(): string {
    if (isUser) return "You";
    if (isSystem) return "System";
    return agent?.name || "Agent";
  }
</script>

<article
  class="flex gap-3 p-3 rounded-lg {isUser ? 'bg-surface-900/50' : isSystem ? 'bg-red-950/30 border border-red-900/40' : 'bg-surface-900'}"
  aria-label="{getRoleLabel()} message"
>
  <div
    class="w-8 h-8 rounded-full {isUser ? 'bg-surface-700' : isSystem ? 'bg-red-900/60' : 'bg-ashwen-700'} flex items-center justify-center text-sm flex-shrink-0"
    aria-hidden="true"
  >
    {#if isUser}
      Y
    {:else if isSystem}
      !
    {:else}
      {agent?.name?.[0] || "?"}
    {/if}
  </div>
  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-sm font-medium {isUser ? 'text-surface-200' : isSystem ? 'text-red-300' : 'text-ashwen-400'}">
        {#if isUser}
          You
        {:else if isSystem}
          System
        {:else}
          {agent?.name || "Agent"}
        {/if}
      </span>
      {#if isDm}
        <span class="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-ashwen-900/60 text-ashwen-300 border border-ashwen-700/50" aria-label="Direct message">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          DM
        </span>
      {/if}
      {#if msg.confidence !== null}
        <span class="text-xs px-1.5 py-0.5 rounded bg-surface-800 text-surface-400" aria-label="Confidence {Math.round(msg.confidence * 100)}%">
          {Math.round(msg.confidence * 100)}%
        </span>
      {/if}
      <time class="text-xs text-surface-600" datetime={msg.created_at}>
        {new Date(msg.created_at).toLocaleTimeString()}
      </time>
    </div>
    <div class="mt-1 text-surface-200 whitespace-pre-wrap break-words">
      {msg.content}
    </div>
  </div>
</article>
