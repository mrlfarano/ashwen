<script lang="ts">
  import { getErrorMessage, memoryApi } from "$lib/api/rest";
  import type { MemoryEntry } from "$lib/api/types";
  import { onMount } from "svelte";
  import ErrorAlert from "$lib/components/ui/ErrorAlert.svelte";
  import MemorySkeleton from "$lib/components/ui/MemorySkeleton.svelte";

  interface Props {
    projectId: string;
  }

  let { projectId }: Props = $props();

  let allEntries = $state<MemoryEntry[]>([]);
  let entries = $state<MemoryEntry[]>([]);
  let loading = $state(true);
  let error = $state("");
  let searchQuery = $state("");
  let selectedType = $state("");
  let dateFrom = $state("");
  let dateTo = $state("");
  let showFilters = $state(false);

  // Pagination state
  let currentPage = $state(1);
  let pageSize = $state(10);
  let totalCount = $state(0);
  let totalPages = $state(1);

  // Inline editing state
  let editingId = $state<string | null>(null);
  let editTitle = $state("");
  let editContent = $state("");
  let editMetadata = $state("");
  let saveError = $state<string | null>(null);
  let saving = $state(false);

  // Metadata expansion state
  let expandedMetadata = $state<Set<string>>(new Set());

  const memoryTypes = ["decision", "pattern", "context", "learning", "note"];

  onMount(async () => {
    await loadMemory();
  });

  async function loadMemory() {
    loading = true;
    error = "";
    try {
      allEntries = await memoryApi.list(projectId, selectedType || undefined);
      applyDateFilter();
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to load memory");
    } finally {
      loading = false;
    }
  }

  async function search() {
    if (!searchQuery.trim()) {
      await loadMemory();
      return;
    }
    loading = true;
    error = "";
    try {
      allEntries = await memoryApi.search(projectId, searchQuery, selectedType || undefined);
      applyDateFilter();
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to search memory");
    } finally {
      loading = false;
    }
  }

  function filterByType(type: string) {
    selectedType = selectedType === type ? "" : type;
    currentPage = 1;
    loadMemory();
  }

  function applyDateFilter() {
    let filtered = [...allEntries];

    if (dateFrom) {
      const fromDate = new Date(dateFrom);
      fromDate.setHours(0, 0, 0, 0);
      filtered = filtered.filter(e => new Date(e.created_at) >= fromDate);
    }

    if (dateTo) {
      const toDate = new Date(dateTo);
      toDate.setHours(23, 59, 59, 999);
      filtered = filtered.filter(e => new Date(e.created_at) <= toDate);
    }

    entries = filtered;
    totalCount = entries.length;
    totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
    currentPage = 1;
  }

  function clearFilters() {
    selectedType = "";
    dateFrom = "";
    dateTo = "";
    searchQuery = "";
    currentPage = 1;
    loadMemory();
  }

  function getPaginatedEntries(): MemoryEntry[] {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return entries.slice(start, end);
  }

  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages) {
      currentPage = page;
    }
  }

  function startEdit(entry: MemoryEntry) {
    editingId = entry.id;
    editTitle = entry.title;
    editContent = entry.content;
    editMetadata = JSON.stringify(entry.metadata, null, 2);
    saveError = null;
  }

  function cancelEdit() {
    editingId = null;
    editTitle = "";
    editContent = "";
    editMetadata = "";
    saveError = null;
  }

  async function saveEdit(entryId: string) {
    saving = true;
    saveError = null;
    
    try {
      let metadataObj: Record<string, unknown> = {};
      if (editMetadata.trim()) {
        try {
          metadataObj = JSON.parse(editMetadata);
        } catch {
          saveError = "Invalid JSON in metadata";
          saving = false;
          return;
        }
      }

      const updated = await memoryApi.update(entryId, {
        title: editTitle,
        content: editContent,
        metadata: metadataObj,
      });

      allEntries = allEntries.map((entry) =>
        entry.id === entryId ? updated : entry
      );
      applyDateFilter();
      cancelEdit();
    } catch (e: unknown) {
      saveError = getErrorMessage(e, "Failed to save");
    } finally {
      saving = false;
    }
  }

  async function deleteEntry(entryId: string) {
    if (!confirm("Delete this memory entry?")) return;

    error = "";
    try {
      await memoryApi.delete(entryId);
      allEntries = allEntries.filter((entry) => entry.id !== entryId);
      applyDateFilter();
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to delete memory entry");
    }
  }

  function toggleMetadata(id: string) {
    const newSet = new Set(expandedMetadata);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    expandedMetadata = newSet;
  }

  function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  $effect(() => {
    dateFrom;
    dateTo;
    applyDateFilter();
  });
</script>

<div class="flex-1 flex flex-col" role="region" aria-label="Memory panel">
  <div class="p-4 border-b border-surface-800">
    {#if error}
      <div class="mb-3">
        <ErrorAlert title="Memory error" message={error} onDismiss={() => error = ""} />
      </div>
    {/if}

    <div class="flex items-center justify-between mb-3">
      <h3 class="font-medium">Memory</h3>
      <button
        onclick={() => showFilters = !showFilters}
        aria-expanded={showFilters}
        aria-controls="filters-panel"
        class="text-xs px-2 py-1 rounded bg-surface-800 hover:bg-surface-700 flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-ashwen-500"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clip-rule="evenodd" />
        </svg>
        Filters
      </button>
    </div>

    <form class="flex gap-2 mb-3" onsubmit={(e) => { e.preventDefault(); search(); }}>
      <label class="sr-only" for="memory-search">Search memory</label>
      <input
        id="memory-search"
        type="text"
        bind:value={searchQuery}
        placeholder="Search memory..."
        aria-label="Search memory"
        class="flex-1 bg-surface-900 border border-surface-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ashwen-500"
      />
      <button
        type="submit"
        class="px-3 py-1.5 bg-surface-800 hover:bg-surface-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ashwen-500"
      >
        Search
      </button>
    </form>

    {#if showFilters}
      <div id="filters-panel" class="mb-3 p-3 bg-surface-900 rounded-lg space-y-3">
        <fieldset>
          <legend class="text-xs text-surface-400 mb-1">Memory Type</legend>
          <div class="flex gap-2 flex-wrap" role="group">
            {#each memoryTypes as type}
              <button
                onclick={() => filterByType(type)}
                aria-pressed={selectedType === type}
                class="px-2 py-1 rounded text-xs {selectedType === type ? 'bg-ashwen-600' : 'bg-surface-800 hover:bg-surface-700'} focus:outline-none focus:ring-2 focus:ring-ashwen-500"
              >
                {type}
              </button>
            {/each}
          </div>
        </fieldset>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-xs text-surface-400 mb-1 block" for="date-from">From Date</label>
            <input
              id="date-from"
              type="date"
              bind:value={dateFrom}
              class="w-full bg-surface-800 border border-surface-700 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ashwen-500"
            />
          </div>
          <div>
            <label class="text-xs text-surface-400 mb-1 block" for="date-to">To Date</label>
            <input
              id="date-to"
              type="date"
              bind:value={dateTo}
              class="w-full bg-surface-800 border border-surface-700 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ashwen-500"
            />
          </div>
        </div>

        <div class="flex justify-end">
          <button
            onclick={clearFilters}
            class="text-xs px-2 py-1 text-surface-400 hover:text-surface-200 focus:outline-none focus:ring-2 focus:ring-ashwen-500 rounded"
          >
            Clear Filters
          </button>
        </div>
      </div>
    {:else}
      <div class="flex gap-2" role="group" aria-label="Memory type filters">
        {#each memoryTypes as type}
          <button
            onclick={() => filterByType(type)}
            aria-pressed={selectedType === type}
            class="px-2 py-1 rounded text-xs {selectedType === type ? 'bg-ashwen-600' : 'bg-surface-800 hover:bg-surface-700'} focus:outline-none focus:ring-2 focus:ring-ashwen-500"
          >
            {type}
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="flex-1 overflow-y-auto p-4" role="feed" aria-label="Memory entries">
    {#if loading}
      <MemorySkeleton count={4} />
    {:else if entries.length === 0}
      <div class="text-surface-500 text-center py-8" role="status">
        No memory entries yet
      </div>
    {:else}
      <ul class="space-y-3">
        {#each getPaginatedEntries() as entry (entry.id)}
        <li>
          <article class="p-3 bg-surface-900 rounded-lg border border-surface-800 hover:border-surface-700 transition-colors" aria-labelledby="entry-title-{entry.id}">
            {#if editingId === entry.id}
              <!-- Edit Mode -->
              <form class="space-y-2" onsubmit={(e) => { e.preventDefault(); saveEdit(entry.id); }}>
                <label class="sr-only" for="edit-title-{entry.id}">Title</label>
                <input
                  id="edit-title-{entry.id}"
                  type="text"
                  bind:value={editTitle}
                  class="w-full bg-surface-800 border border-surface-700 rounded px-2 py-1 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-ashwen-500"
                  placeholder="Title"
                />
                <label class="sr-only" for="edit-content-{entry.id}">Content</label>
                <textarea
                  id="edit-content-{entry.id}"
                  bind:value={editContent}
                  rows="4"
                  class="w-full bg-surface-800 border border-surface-700 rounded px-2 py-1 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ashwen-500"
                  placeholder="Content"
                ></textarea>
                <div>
                  <label class="text-xs text-surface-400 mb-1 block" for="edit-metadata-{entry.id}">Metadata (JSON)</label>
                  <textarea
                    id="edit-metadata-{entry.id}"
                    bind:value={editMetadata}
                    rows="2"
                    class="w-full bg-surface-800 border border-surface-700 rounded px-2 py-1 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-ashwen-500"
                    placeholder="JSON metadata"
                  ></textarea>
                </div>

                {#if saveError}
                  <div class="text-xs text-red-400" role="alert">{saveError}</div>
                {/if}

                <div class="flex gap-2">
                  <button
                    type="submit"
                    disabled={saving}
                    aria-busy={saving}
                    class="px-3 py-1 bg-ashwen-600 hover:bg-ashwen-700 disabled:bg-surface-700 rounded text-xs focus:outline-none focus:ring-2 focus:ring-ashwen-500"
                  >
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button
                    type="button"
                    onclick={cancelEdit}
                    disabled={saving}
                    class="px-3 py-1 bg-surface-700 hover:bg-surface-600 rounded text-xs focus:outline-none focus:ring-2 focus:ring-ashwen-500"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            {:else}
              <!-- View Mode -->
              <div class="flex items-start justify-between gap-2 mb-2">
                <div class="flex items-center gap-2 flex-1">
                  <span class="text-xs px-1.5 py-0.5 rounded bg-surface-700 uppercase">{entry.memory_type}</span>
                  <span id="entry-title-{entry.id}" class="text-sm font-medium">{entry.title}</span>
                </div>
                <div class="flex gap-1">
                  <button
                    onclick={() => startEdit(entry)}
                    aria-label="Edit {entry.title}"
                    class="p-1 hover:bg-surface-700 rounded text-surface-400 hover:text-surface-200 focus:outline-none focus:ring-2 focus:ring-ashwen-500"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </button>
                  <button
                    onclick={() => deleteEntry(entry.id)}
                    aria-label="Delete {entry.title}"
                    class="p-1 hover:bg-red-900/50 rounded text-surface-400 hover:text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>

              <p class="text-sm text-surface-400 mb-2">{entry.content}</p>

              <!-- Metadata -->
              {#if Object.keys(entry.metadata).length > 0}
                <div class="mb-2">
                  <button
                    onclick={() => toggleMetadata(entry.id)}
                    aria-expanded={expandedMetadata.has(entry.id)}
                    aria-controls="metadata-{entry.id}"
                    class="text-xs text-surface-500 hover:text-surface-300 flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-ashwen-500 rounded"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 transition-transform {expandedMetadata.has(entry.id) ? 'rotate-90' : ''}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                    Metadata ({Object.keys(entry.metadata).length})
                  </button>

                  {#if expandedMetadata.has(entry.id)}
                    <div id="metadata-{entry.id}" class="mt-1 p-2 bg-surface-800 rounded text-xs font-mono text-surface-400 overflow-x-auto">
                      <pre>{JSON.stringify(entry.metadata, null, 2)}</pre>
                    </div>
                  {/if}
                </div>
              {/if}

              <!-- Timestamps & File Path -->
              <div class="flex items-center justify-between text-xs text-surface-600">
                <div class="flex items-center gap-3">
                  <time datetime={entry.created_at} title="Created">Created: {formatDate(entry.created_at)}</time>
                  <time datetime={entry.updated_at} title="Updated">Updated: {formatDate(entry.updated_at)}</time>
                </div>
                {#if entry.file_path}
                  <span class="text-surface-500 truncate max-w-[200px]" title={entry.file_path}>
                    📄 {entry.file_path}
                  </span>
                {/if}
              </div>
            {/if}
          </article>
        </li>
      {/each}
      </ul>

      <!-- Pagination -->
      {#if totalPages > 1}
        <nav class="mt-4 flex items-center justify-center gap-2" aria-label="Memory pagination">
          <button
            onclick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            aria-label="Go to previous page"
            class="px-2 py-1 bg-surface-800 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs focus:outline-none focus:ring-2 focus:ring-ashwen-500"
          >
            Previous
          </button>

          <div class="flex items-center gap-1" role="group" aria-label="Page numbers">
            {#each Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let page: number;
              if (totalPages <= 5) {
                page = i + 1;
              } else if (currentPage <= 3) {
                page = i + 1;
              } else if (currentPage >= totalPages - 2) {
                page = totalPages - 4 + i;
              } else {
                page = currentPage - 2 + i;
              }
              return page;
            }) as page (page)}
              <button
                onclick={() => goToPage(page)}
                aria-label="Go to page {page}"
                aria-current={currentPage === page ? 'page' : undefined}
                class="w-7 h-7 flex items-center justify-center rounded text-xs {currentPage === page ? 'bg-ashwen-600' : 'bg-surface-800 hover:bg-surface-700'} focus:outline-none focus:ring-2 focus:ring-ashwen-500"
              >
                {page}
              </button>
            {/each}
          </div>

          <button
            onclick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            aria-label="Go to next page"
            class="px-2 py-1 bg-surface-800 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs focus:outline-none focus:ring-2 focus:ring-ashwen-500"
          >
            Next
          </button>

          <span class="text-xs text-surface-500 ml-2" aria-live="polite">
            {totalCount} entries
          </span>
        </nav>
      {/if}
    {/if}
  </div>
</div>
