<script lang="ts">
  import { onMount } from "svelte";

  interface ConsentState {
    crashReporting: boolean;
    productAnalytics: boolean;
    hasPrompted: boolean;
  }

  let visible = $state(false);
  let loading = $state(true);
  let saving = $state(false);
  let consent = $state<ConsentState>({
    crashReporting: false,
    productAnalytics: false,
    hasPrompted: false
  });

  onMount(async () => {
    await checkConsent();
  });

  async function checkConsent() {
    loading = true;
    try {
      // Check if we should show the prompt
      const shouldPrompt = await window.ashwen?.analytics?.shouldPrompt?.();
      if (shouldPrompt) {
        // Get current consent state
        consent = await window.ashwen?.analytics?.getConsent?.() || consent;
        visible = true;
      }
    } catch (err) {
      console.error("[Analytics] Failed to check consent:", err);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    try {
      await window.ashwen?.analytics?.setConsent?.({
        crashReporting: consent.crashReporting,
        productAnalytics: consent.productAnalytics
      });
      visible = false;
    } catch (err) {
      console.error("[Analytics] Failed to save consent:", err);
    } finally {
      saving = false;
    }
  }

  async function handleSkip() {
    try {
      await window.ashwen?.analytics?.markPrompted?.();
      visible = false;
    } catch (err) {
      console.error("[Analytics] Failed to mark prompted:", err);
      visible = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      handleSkip();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if visible}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    on:click={handleSkip}
    on:keydown={handleKeydown}
  >
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      class="bg-surface-900 border border-surface-700 rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden"
      on:click={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="px-6 py-5 border-b border-surface-800">
        <h2 id="consent-title" class="text-xl font-semibold text-white">
          Help Improve Ashwen
        </h2>
        <p class="text-sm text-surface-400 mt-1">
          Choose what data you're comfortable sharing
        </p>
      </div>

      <!-- Content -->
      <div class="px-6 py-5 space-y-5">
        <!-- Privacy notice -->
        <div class="flex items-start gap-3 p-3 rounded-lg bg-surface-800/50 border border-surface-700">
          <svg class="w-5 h-5 text-ashwen-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <div class="text-sm text-surface-300">
            <strong>Local-first privacy:</strong> Your project data, code, and conversations 
            never leave your device. Only anonymous usage patterns and crash reports are sent.
          </div>
        </div>

        <!-- Crash reporting option -->
        <label class="flex items-start gap-3 cursor-pointer group">
          <div class="relative flex items-center justify-center mt-1">
            <input
              type="checkbox"
              bind:checked={consent.crashReporting}
              class="sr-only peer"
            />
            <div class="w-5 h-5 rounded border-2 border-surface-600 bg-surface-800 peer-checked:bg-ashwen-600 peer-checked:border-ashwen-500 transition-colors">
              {#if consent.crashReporting}
                <svg class="w-full h-full text-white p-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              {/if}
            </div>
          </div>
          <div class="flex-1">
            <div class="font-medium text-white group-hover:text-ashwen-300 transition-colors">
              Crash Reporting
            </div>
            <p class="text-sm text-surface-400 mt-0.5">
              Automatically send anonymous crash reports to help fix bugs. 
              Includes stack traces and app version — no personal data.
            </p>
          </div>
        </label>

        <!-- Product analytics option -->
        <label class="flex items-start gap-3 cursor-pointer group">
          <div class="relative flex items-center justify-center mt-1">
            <input
              type="checkbox"
              bind:checked={consent.productAnalytics}
              class="sr-only peer"
            />
            <div class="w-5 h-5 rounded border-2 border-surface-600 bg-surface-800 peer-checked:bg-ashwen-600 peer-checked:border-ashwen-500 transition-colors">
              {#if consent.productAnalytics}
                <svg class="w-full h-full text-white p-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              {/if}
            </div>
          </div>
          <div class="flex-1">
            <div class="font-medium text-white group-hover:text-ashwen-300 transition-colors">
              Product Analytics
            </div>
            <p class="text-sm text-surface-400 mt-0.5">
              Help us understand how Ashwen is used with anonymous feature usage data. 
              No code or file contents are ever sent.
            </p>
          </div>
        </label>

        <!-- Info note -->
        <div class="text-xs text-surface-500 flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>You can change these preferences anytime in Settings</span>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-surface-800/50 border-t border-surface-700 flex items-center justify-end gap-3">
        <button
          onclick={handleSkip}
          disabled={saving}
          class="px-4 py-2 rounded-lg text-sm font-medium text-surface-400 hover:text-white hover:bg-surface-700 transition-colors disabled:opacity-50"
        >
          Skip for now
        </button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="px-5 py-2 rounded-lg text-sm font-medium bg-ashwen-600 hover:bg-ashwen-500 text-white transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          {/if}
          Save Preferences
        </button>
      </div>
    </div>
  </div>
{/if}
