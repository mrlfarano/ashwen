<script lang="ts">
  import Skeleton from './Skeleton.svelte';

  interface Props {
    /** Number of skeleton entries to render */
    count?: number;
  }

  let { count = 4 }: Props = $props();
</script>

<div class="space-y-3">
  {#each Array(count) as _, i}
    <div class="p-3 bg-surface-900 rounded-lg">
      <div class="flex items-center gap-2 mb-2">
        <Skeleton width="4rem" height="1.25rem" />
        <Skeleton width="8rem" height="1rem" />
      </div>
      <Skeleton lines={2} gap="0.375rem" />
      <div class="mt-2">
        <Skeleton width="5rem" height="0.75rem" />
      </div>
    </div>
  {/each}
</div>
