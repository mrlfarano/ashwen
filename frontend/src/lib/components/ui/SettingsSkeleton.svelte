<script lang="ts">
  import Skeleton from './Skeleton.svelte';
</script>

<div class="flex-1 overflow-y-auto p-6 space-y-6">
  <!-- Header -->
  <div>
    <Skeleton width="30%" height="1.5rem" class="mb-2" />
    <Skeleton width="50%" height="0.875rem" />
  </div>

  <!-- Info Cards -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    {#each Array(3) as _}
      <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
        <Skeleton width="40%" height="0.75rem" class="mb-2" />
        <Skeleton width="60%" height="1.125rem" />
      </div>
    {/each}
  </div>

  <!-- Provider Cards -->
  <div class="space-y-4">
    {#each Array(3) as _}
      <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1">
            <Skeleton width="30%" height="1.125rem" class="mb-1" />
            <Skeleton width="80%" height="0.875rem" />
          </div>
          <Skeleton width="5rem" height="2rem" />
        </div>
        <div class="mt-4 flex gap-2">
          <Skeleton width="100%" height="2.5rem" />
          <Skeleton width="4rem" height="2.5rem" />
        </div>
      </div>
    {/each}
  </div>
</div>
