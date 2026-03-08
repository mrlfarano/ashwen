<script lang="ts">
  import { page } from "$app/stores";
  import { onMount } from "svelte";
  import { project, agents, messages, ui } from "$lib/stores";
  import { agentsApi, getErrorMessage, projectsApi } from "$lib/api/rest";
  import { websocket } from "$lib/api/websocket";
  import AgentCard from "$lib/components/agents/AgentCard.svelte";
  import GroupChat from "$lib/components/chat/GroupChat.svelte";
  import MemoryPanel from "$lib/components/memory/MemoryPanel.svelte";
  import SettingsPanel from "$lib/components/settings/SettingsPanel.svelte";
  import ErrorAlert from "$lib/components/ui/ErrorAlert.svelte";
  import WorkspaceSkeleton from "$lib/components/ui/WorkspaceSkeleton.svelte";

  const projectId = $derived($page.params.id);
  let loading = $state(true);
  let error = $state("");

  onMount(async () => {
    await loadWorkspace();

    return () => {
      websocket.disconnect();
      project.clear();
      agents.clear();
      messages.clear();
      ui.clearSelection();
    };
  });

  async function loadWorkspace() {
    loading = true;
    error = "";
    try {
      ui.clearSelection();

      const p = await projectsApi.get(projectId);
      project.set(p);

      let agentList = await agentsApi.list(projectId);
      if (agentList.length === 0) {
        await agentsApi.initialize(projectId);
        agentList = await agentsApi.list(projectId);
      }
      agents.set(agentList);

      // Load historical messages
      const messageHistory = await projectsApi.getMessages(projectId);
      messages.set(messageHistory);

      websocket.connect(projectId);
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to load workspace");
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Ashwen - {$project?.name || 'Project'}</title>
</svelte:head>

{#if loading}
  <WorkspaceSkeleton />
{:else if error}
  <div class="flex-1 flex items-center justify-center p-8">
    <div class="w-full max-w-md">
      <ErrorAlert 
        title="Failed to load workspace" 
        message={error}
        onRetry={loadWorkspace}
      />
    </div>
  </div>
{:else}
  <div class="flex-1 flex">
    <!-- Agents Panel -->
    <aside class="w-64 border-r border-surface-800 flex flex-col" aria-label="Agents panel">
      <div class="p-3 border-b border-surface-800">
        <h3 class="font-medium text-sm text-surface-400">Agents</h3>
      </div>
      <ul class="flex-1 overflow-y-auto p-2 space-y-1" role="listbox" aria-label="Available agents">
        {#each $agents as agent}
          <li>
            <AgentCard {agent} />
          </li>
        {/each}
      </ul>
    </aside>

    <!-- Main Panel -->
    <main class="flex-1 flex flex-col" aria-label="Main content">
      {#if $ui.activeTab === "chat"}
        <GroupChat />
      {:else if $ui.activeTab === "memory"}
        <MemoryPanel projectId={projectId} />
      {:else}
        <SettingsPanel />
      {/if}
    </main>
  </div>
{/if}
