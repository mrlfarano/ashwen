<script lang="ts">
  import Skeleton from './Skeleton.svelte';

  interface Props {
    count?: number;
  }

  let { count = 3 }: Props = $props();
</script>

<div class="space-y-2 mb-4">
  {#each Array(count) as _, i}
    <div class="p-4 rounded-lg bg-surface-900">
      <Skeleton width="60%" height="1.25rem" class="mb-2" />
      <Skeleton width="80%" height="0.875rem" />
    </div>
  {/each}
</div>
