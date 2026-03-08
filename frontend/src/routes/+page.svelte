<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { getErrorMessage, projectsApi } from "$lib/api/rest";
  import type { Project } from "$lib/api/types";
  import ErrorAlert from "$lib/components/ui/ErrorAlert.svelte";
  import ProjectSkeleton from "$lib/components/ui/ProjectSkeleton.svelte";

  let projects = $state<Project[]>([]);
  let loading = $state(true);
  let error = $state("");
  let creating = $state(false);

  onMount(async () => {
    await loadProjects();
  });

  async function loadProjects() {
    loading = true;
    error = "";
    try {
      projects = await projectsApi.list();
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to load projects");
    } finally {
      loading = false;
    }
  }

  async function selectProject(p: Project) {
    goto(`/projects/${p.id}`);
  }

  async function createProject() {
    const name = prompt("Project name:");
    const path = prompt("Project path:");
    if (name && path) {
      creating = true;
      try {
        const project = await projectsApi.create({ name, path });
        projects = [...projects, project];
        await goto(`/projects/${project.id}`);
      } catch (e: unknown) {
        error = getErrorMessage(e, "Failed to create project");
      } finally {
        creating = false;
      }
    }
  }

  function dismissError() {
    error = "";
  }
</script>

<svelte:head>
  <title>Ashwen - Projects</title>
</svelte:head>

<div class="flex-1 flex items-center justify-center p-8">
  <div class="w-full max-w-2xl">
    <h2 class="text-2xl font-bold mb-6">Select a Project</h2>

    {#if error}
      <div class="mb-4">
        <ErrorAlert
          title="Failed to load projects"
          message={error}
          onRetry={loadProjects}
          onDismiss={dismissError}
        />
      </div>
    {/if}

    {#if loading}
      <ProjectSkeleton count={3} />
    {:else}
      <ul class="space-y-2 mb-4" role="listbox" aria-label="Projects">
        {#each projects as p}
          <li>
            <button
              onclick={() => selectProject(p)}
              role="option"
              aria-label="Select project {p.name}"
              class="w-full text-left p-4 rounded-lg bg-surface-900 hover:bg-surface-800 transition-colors focus:outline-none focus:ring-2 focus:ring-ashwen-500"
            >
              <div class="font-medium">{p.name}</div>
              <div class="text-sm text-surface-500">{p.path}</div>
            </button>
          </li>
        {:else}
          <li class="text-surface-500 py-4 text-center">
            <p class="mb-2">No projects yet</p>
            <p class="text-sm">Create your first project to get started</p>
          </li>
        {/each}
      </ul>

      <button
        onclick={createProject}
        disabled={creating}
        aria-busy={creating}
        class="px-4 py-2 bg-ashwen-600 hover:bg-ashwen-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-ashwen-400 focus:ring-offset-2 focus:ring-offset-surface-950"
      >
        {creating ? 'Creating...' : '+ New Project'}
      </button>
    {/if}
  </div>
</div>
