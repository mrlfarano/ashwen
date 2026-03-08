<script lang="ts">
  /**
   * ErrorBoundary Component
   * Gracefully handles and displays errors in the UI.
   * Wraps child components and catches any unhandled errors.
   */

  interface Props {
    children: import("svelte").Snippet;
    fallback?: import("svelte").Snippet<
      [{ error: Error; reset: () => void; errorInfo?: string }]
    >;
    onError?: (error: Error, errorInfo?: string) => void;
    showDetails?: boolean;
  }

  let {
    children,
    fallback,
    onError,
    showDetails = false
  }: Props = $props();

  let hasError = $state(false);
  let error = $state<Error | null>(null);
  let errorInfo = $state<string | undefined>(undefined);

  /**
   * Reset the error boundary and re-render children
   */
  function reset() {
    hasError = false;
    error = null;
    errorInfo = undefined;
  }

  /**
   * Handle caught errors
   */
  function handleError(event: ErrorEvent) {
    hasError = true;
    error = event.error instanceof Error ? event.error : new Error(String(event.error));
    errorInfo = event.message;
    
    // Call optional error handler
    if (onError) {
      onError(error, errorInfo);
    }
    
    // Prevent the error from propagating further
    event.preventDefault();
  }

  /**
   * Handle unhandled promise rejections
   */
  function handleRejection(event: PromiseRejectionEvent) {
    hasError = true;
    error = event.reason instanceof Error 
      ? event.reason 
      : new Error(String(event.reason));
    errorInfo = "Unhandled Promise Rejection";
    
    if (onError) {
      onError(error, errorInfo);
    }
    
    event.preventDefault();
  }

  // Set up error listeners on mount
  $effect(() => {
    // Use capture phase to catch errors before they propagate
    window.addEventListener("error", handleError, true);
    window.addEventListener("unhandledrejection", handleRejection, true);
    
    return () => {
      window.removeEventListener("error", handleError, true);
      window.removeEventListener("unhandledrejection", handleRejection, true);
    };
  });
</script>

{#if hasError && error}
  {@const resetFn = reset}
  {#if fallback}
    {@render fallback({ error, reset: resetFn, errorInfo })}
  {:else}
    <!-- Default error UI -->
    <div class="flex flex-col items-center justify-center p-6 m-4 rounded-lg bg-red-950/30 border border-red-900/40">
      <!-- Error Icon -->
      <div class="w-12 h-12 mb-4 rounded-full bg-red-900/60 flex items-center justify-center">
        <svg class="w-6 h-6 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path 
            stroke-linecap="round" 
            stroke-linejoin="round" 
            stroke-width="2" 
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
          />
        </svg>
      </div>
      
      <!-- Error Title -->
      <h3 class="text-lg font-semibold text-red-300 mb-2">
        Something went wrong
      </h3>
      
      <!-- Error Message -->
      <p class="text-sm text-surface-300 text-center max-w-md mb-4">
        {error.message || "An unexpected error occurred"}
      </p>
      
      <!-- Error Details (toggleable) -->
      {#if showDetails && (error.stack || errorInfo)}
        <details class="w-full max-w-lg mb-4">
          <summary class="cursor-pointer text-xs text-surface-500 hover:text-surface-400 transition-colors">
            View technical details
          </summary>
          <pre class="mt-2 p-3 text-xs bg-surface-950 rounded border border-surface-800 overflow-auto max-h-40 text-surface-400 font-mono">
{#if errorInfo}{errorInfo}\n{/if}{error.stack || error.message}</pre>
        </details>
      {/if}
      
      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="button"
          onclick={reset}
          class="px-4 py-2 text-sm font-medium rounded-lg bg-surface-800 text-surface-200 hover:bg-surface-700 transition-colors"
        >
          Try again
        </button>
        <button
          type="button"
          onclick={() => window.location.reload()}
          class="px-4 py-2 text-sm font-medium rounded-lg bg-red-900/60 text-red-200 hover:bg-red-900/80 transition-colors"
        >
          Reload page
        </button>
      </div>
    </div>
  {/if}
{:else}
  {@render children()}
{/if}
