<script lang="ts">
  import type { Agent } from "$lib/stores";
  import { ui } from "$lib/stores";

  interface Props {
    agent: Agent;
  }

  let { agent }: Props = $props();

  const statusColors = {
    idle: "bg-surface-600",
    thinking: "bg-yellow-500 animate-pulse",
    active: "bg-green-500",
  };

  const statusLabels = {
    idle: "Idle",
    thinking: "Thinking",
    active: "Active",
  };

  const isSelected = $derived($ui.selectedAgentId === agent.id);
  const isDmTarget = $derived($ui.dmMode && isSelected);
</script>

<button
  onclick={() => ui.selectAgent(agent.id)}
  role="option"
  aria-selected={isSelected}
  aria-label="{agent.name}, {statusLabels[agent.status]}{isDmTarget ? ', direct message mode' : ''}"
  class="w-full text-left p-2 rounded-lg transition-colors hover:bg-surface-800 {isSelected ? 'bg-surface-800 ring-1 ring-ashwen-500' : ''} focus:outline-none focus:ring-2 focus:ring-ashwen-500"
>
  <div class="flex items-center gap-2">
    <div class="w-2 h-2 rounded-full {statusColors[agent.status]}" aria-hidden="true"></div>
    <span class="font-medium text-sm">{agent.name}</span>
    {#if isDmTarget}
      <span class="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-ashwen-700/50 text-ashwen-300">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        DM
      </span>
    {/if}
  </div>
  <div class="text-xs text-surface-500 mt-1 truncate">{agent.persona}</div>
</button>
