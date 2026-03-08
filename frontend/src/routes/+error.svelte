<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { fly } from 'svelte/transition';

  interface ErrorWithDetails {
    message: string;
    status?: number;
    statusText?: string;
    stack?: string;
  }

  function getErrorDetails(): ErrorWithDetails {
    const error = $page.error as Error & { statusText?: string } | undefined;
    return {
      message: error?.message || 'An unexpected error occurred',
      status: $page.status,
      statusText: error?.statusText,
      stack: error?.stack
    };
  }

  function goHome() {
    goto('/');
  }

  function goBack() {
    window.history.back();
  }

  function reload() {
    window.location.reload();
  }

  function getStatusMessage(status: number | undefined): string {
    switch (status) {
      case 400:
        return 'Bad Request';
      case 401:
        return 'Unauthorized';
      case 403:
        return 'Forbidden';
      case 404:
        return 'Page Not Found';
      case 500:
        return 'Internal Server Error';
      case 502:
        return 'Bad Gateway';
      case 503:
        return 'Service Unavailable';
      default:
        return 'Error';
    }
  }

  let errorDetails = $derived(getErrorDetails());
</script>

<svelte:head>
  <title>Error - Ashwen</title>
</svelte:head>

<div 
  class="flex-1 flex items-center justify-center p-8 bg-surface-950"
  in:fly={{ y: 20, duration: 300 }}
  role="alert"
  aria-live="assertive"
>
  <div class="w-full max-w-lg">
    <!-- Error Card -->
    <div class="rounded-xl border border-red-900/40 bg-red-950/20 p-8 shadow-xl">
      <!-- Status Code Badge -->
      {#if errorDetails.status}
        <div class="flex items-center gap-3 mb-6">
          <span class="px-3 py-1 text-sm font-mono font-bold bg-red-900/50 text-red-300 rounded-full">
            {errorDetails.status}
          </span>
          <span class="text-sm text-red-400 font-medium">
            {getStatusMessage(errorDetails.status)}
          </span>
        </div>
      {/if}

      <!-- Error Icon -->
      <div class="flex justify-center mb-6">
        <div class="w-16 h-16 rounded-full bg-red-900/40 flex items-center justify-center">
          <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path 
              stroke-linecap="round" 
              stroke-linejoin="round" 
              stroke-width="2" 
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
            />
          </svg>
        </div>
      </div>

      <!-- Error Title -->
      <h1 class="text-xl font-bold text-center text-surface-100 mb-3">
        Something went wrong
      </h1>

      <!-- Error Message -->
      <p class="text-sm text-center text-surface-400 mb-6">
        {errorDetails.message}
      </p>

      <!-- Technical Details (collapsible) -->
      {#if errorDetails.stack}
        <details class="mb-6 group">
          <summary class="cursor-pointer text-xs text-surface-500 hover:text-surface-400 transition-colors text-center">
            View technical details
          </summary>
          <pre class="mt-3 p-4 text-xs bg-surface-900 rounded-lg border border-surface-800 overflow-auto max-h-48 text-surface-400 font-mono">
{errorDetails.stack}</pre>
        </details>
      {/if}

      <!-- Action Buttons -->
      <div class="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onclick={goHome}
          class="px-5 py-2.5 text-sm font-medium rounded-lg bg-ashwen-600 hover:bg-ashwen-500 text-white transition-colors flex items-center justify-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Go Home
        </button>
        
        <button
          onclick={goBack}
          class="px-5 py-2.5 text-sm font-medium rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-200 transition-colors flex items-center justify-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Go Back
        </button>
        
        <button
          onclick={reload}
          class="px-5 py-2.5 text-sm font-medium rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-200 transition-colors flex items-center justify-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Reload
        </button>
      </div>
    </div>

    <!-- Help Text -->
    <p class="text-xs text-center text-surface-600 mt-4">
      If this problem persists, please check your connection or contact support.
    </p>
  </div>
</div>
