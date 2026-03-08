<script lang="ts">
  import LoadingSpinner from './LoadingSpinner.svelte';

  interface Props {
    message?: string;
    class?: string;
  }

  let { message = 'Loading...', class: className = '' }: Props = $props();
</script>

<div class="flex items-center justify-center gap-3 p-8 {className}">
  <LoadingSpinner size="md" />
  <span class="text-surface-500">{message}</span>
</div>
