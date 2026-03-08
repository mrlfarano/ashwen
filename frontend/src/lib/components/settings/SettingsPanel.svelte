<script lang="ts">
  import { onMount } from "svelte";
  import { credentialsApi, getErrorMessage } from "$lib/api/rest";
  import ErrorAlert from "$lib/components/ui/ErrorAlert.svelte";
  import LoadingSpinner from "$lib/components/ui/LoadingSpinner.svelte";
  import SettingsSkeleton from "$lib/components/ui/SettingsSkeleton.svelte";

  const providers = ["openai", "anthropic", "ollama"] as const;

  let loading = $state(true);
  let configured = $state<Record<string, boolean>>({});
  let apiKeys = $state<Record<string, string>>({
    openai: "",
    anthropic: "",
    ollama: "",
  });
  let saving = $state<Record<string, boolean>>({});
  let message = $state("");
  let error = $state("");

  // Analytics consent state
  let analyticsConsent = $state({
    crashReporting: false,
    productAnalytics: false,
    hasPrompted: false
  });
  let analyticsSaving = $state(false);

  const appVersion = $derived(
    typeof window !== "undefined" ? window.ashwen?.app?.version || "dev" : "dev"
  );
  const platform = $derived(
    typeof window !== "undefined" ? window.ashwen?.app?.platform || "unknown" : "unknown"
  );
  const backendUrl = $derived(
    typeof window !== "undefined" ? window.ashwen?.backend?.httpUrl || "http://localhost:8000" : "http://localhost:8000"
  );

  onMount(async () => {
    await Promise.all([loadProviders(), loadAnalyticsConsent()]);
  });

  async function loadProviders() {
    loading = true;
    error = "";
    try {
      const results = await Promise.all(
        providers.map(async (provider) => {
          if (provider === "ollama") {
            return [provider, true] as const;
          }
          const result = await credentialsApi.has(provider);
          return [provider, result.configured] as const;
        })
      );

      configured = Object.fromEntries(results);
    } catch (e: unknown) {
      error = getErrorMessage(e, "Failed to load settings");
    } finally {
      loading = false;
    }
  }

  async function loadAnalyticsConsent() {
    try {
      const consent = await window.ashwen?.analytics?.getConsent?.();
      if (consent) {
        analyticsConsent = consent;
      }
    } catch (err) {
      console.warn("Failed to load analytics consent:", err);
    }
  }

  async function saveAnalyticsConsent() {
    analyticsSaving = true;
    try {
      await window.ashwen?.analytics?.setConsent?.({
        crashReporting: analyticsConsent.crashReporting,
        productAnalytics: analyticsConsent.productAnalytics
      });
      message = "Privacy preferences saved";
    } catch (err) {
      error = "Failed to save privacy preferences";
    } finally {
      analyticsSaving = false;
    }
  }

  async function saveProvider(provider: string) {
    const apiKey = apiKeys[provider]?.trim();
    if (!apiKey) {
      error = `Enter an API key for ${provider}`;
      return;
    }

    message = "";
    error = "";
    saving = { ...saving, [provider]: true };

    try {
      await credentialsApi.set(provider, apiKey);
      configured = { ...configured, [provider]: true };
      apiKeys = { ...apiKeys, [provider]: "" };
      message = `${provider} configured successfully`;
    } catch (e: unknown) {
      error = getErrorMessage(e, `Failed to save ${provider}`);
    } finally {
      saving = { ...saving, [provider]: false };
    }
  }

  async function removeProvider(provider: string) {
    message = "";
    error = "";
    saving = { ...saving, [provider]: true };

    try {
      await credentialsApi.delete(provider);
      configured = { ...configured, [provider]: false };
      message = `${provider} removed`;
    } catch (e: unknown) {
      error = getErrorMessage(e, `Failed to remove ${provider}`);
    } finally {
      saving = { ...saving, [provider]: false };
    }
  }

  function dismissMessage() {
    message = "";
  }

  function dismissError() {
    error = "";
  }
</script>

{#if loading}
  <SettingsSkeleton />
{:else}
  <div class="flex-1 overflow-y-auto p-6 space-y-6">
    <div>
      <h2 class="text-xl font-semibold">Settings</h2>
      <p class="text-sm text-surface-500 mt-1">Configure providers and verify your local desktop environment.</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
        <div class="text-xs uppercase tracking-wide text-surface-500">App version</div>
        <div class="mt-2 text-lg font-medium">{appVersion}</div>
      </div>
      <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
        <div class="text-xs uppercase tracking-wide text-surface-500">Platform</div>
        <div class="mt-2 text-lg font-medium">{platform}</div>
      </div>
      <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
        <div class="text-xs uppercase tracking-wide text-surface-500">Backend</div>
        <div class="mt-2 text-sm font-medium break-all">{backendUrl}</div>
      </div>
    </div>

    {#if message}
      <div class="rounded-lg border border-green-900/50 bg-green-950/30 px-4 py-3 flex items-start justify-between gap-3">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <p class="text-sm text-green-300">{message}</p>
        </div>
        <button
          onclick={dismissMessage}
          class="text-green-400 hover:text-green-300 transition-colors"
          aria-label="Dismiss message"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    {/if}

    {#if error}
      <ErrorAlert 
        title="Configuration error" 
        message={error}
        onDismiss={dismissError}
      />
    {/if}

    <div class="space-y-4">
      {#each providers as provider}
        <div class="p-4 rounded-xl bg-surface-900 border border-surface-800">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-medium capitalize">{provider}</h3>
                <span class="text-[11px] px-2 py-0.5 rounded-full {configured[provider] ? 'bg-green-900/50 text-green-300' : 'bg-surface-800 text-surface-400'}">
                  {configured[provider] ? 'Configured' : provider === 'ollama' ? 'Local provider' : 'Not configured'}
                </span>
              </div>
              <p class="text-sm text-surface-500 mt-1">
                {#if provider === 'ollama'}
                  Ollama uses the local/base URL configured in the backend. No API key is required.
                {:else}
                  Store an encrypted API key for {provider}.
                {/if}
              </p>
            </div>

            {#if provider !== 'ollama' && configured[provider]}
              <button
                onclick={() => removeProvider(provider)}
                disabled={saving[provider]}
                class="px-3 py-2 rounded-lg bg-surface-800 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center gap-2"
              >
                {#if saving[provider]}
                  <LoadingSpinner size="sm" />
                {/if}
                Remove
              </button>
            {/if}
          </div>

          {#if provider !== 'ollama'}
            <div class="mt-4 flex gap-2">
              <input
                type="password"
                bind:value={apiKeys[provider]}
                placeholder={`Paste your ${provider} API key`}
                disabled={saving[provider]}
                class="flex-1 bg-surface-950 border border-surface-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ashwen-500 disabled:opacity-50"
              />
              <button
                onclick={() => saveProvider(provider)}
                disabled={saving[provider]}
                class="px-4 py-2 rounded-lg bg-ashwen-600 hover:bg-ashwen-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium flex items-center gap-2 min-w-[5rem]"
              >
                {#if saving[provider]}
                  <LoadingSpinner size="sm" />
                {:else}
                  Save
                {/if}
              </button>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </div>
{/if}
