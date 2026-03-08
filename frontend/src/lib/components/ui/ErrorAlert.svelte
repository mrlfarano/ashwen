<script lang="ts">
  interface Props {
    title?: string;
    message: string;
    onRetry?: () => void;
    onDismiss?: () => void;
  }

  let { title = 'Error', message, onRetry, onDismiss }: Props = $props();
</script>

<div class="rounded-lg border border-red-900/50 bg-red-950/30 p-4" role="alert">
  <div class="flex items-start gap-3">
    <!-- Error Icon -->
    <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
    </svg>
    
    <div class="flex-1 min-w-0">
      <h3 class="text-sm font-medium text-red-300">{title}</h3>
      <p class="text-sm text-red-200 mt-1">{message}</p>
      
      <!-- Action Buttons -->
      {#if onRetry || onDismiss}
        <div class="mt-3 flex gap-2">
          {#if onRetry}
            <button
              onclick={onRetry}
              class="px-3 py-1.5 text-sm font-medium rounded-lg bg-red-900/50 hover:bg-red-900/70 text-red-200 transition-colors"
            >
              Retry
            </button>
          {/if}
          {#if onDismiss}
            <button
              onclick={onDismiss}
              class="px-3 py-1.5 text-sm font-medium rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-300 transition-colors"
            >
              Dismiss
            </button>
          {/if}
        </div>
      {/if}
    </div>

    {#if onDismiss}
      <button
        onclick={onDismiss}
        class="text-red-400 hover:text-red-300 transition-colors"
        aria-label="Dismiss error"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
        </svg>
      </button>
    {/if}
  </div>
</div>
