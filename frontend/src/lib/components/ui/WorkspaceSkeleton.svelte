<script lang="ts">
  import Skeleton from './Skeleton.svelte';
</script>

<div class="flex-1 flex">
  <!-- Agents Panel Skeleton -->
  <div class="w-64 border-r border-surface-800 flex flex-col">
    <div class="p-3 border-b border-surface-800">
      <Skeleton width="40%" height="0.875rem" />
    </div>
    <div class="flex-1 overflow-y-auto p-2 space-y-1">
      {#each Array(5) as _}
        <div class="p-2 rounded-lg bg-surface-900">
          <div class="flex items-center gap-2">
            <Skeleton width="2rem" height="2rem" variant="circular" />
            <Skeleton width="60%" height="0.875rem" />
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Main Panel Skeleton -->
  <div class="flex-1 flex flex-col">
    <div class="flex-1 flex items-center justify-center">
      <Skeleton width="50%" height="3rem" />
    </div>
  </div>
</div>
