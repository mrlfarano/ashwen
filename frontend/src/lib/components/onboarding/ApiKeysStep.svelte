<script lang="ts">
  import { onboarding } from "$lib/stores/onboarding";
  import { credentialsApi, getErrorMessage } from "$lib/api/rest";
  import LoadingSpinner from "$lib/components/ui/LoadingSpinner.svelte";

  interface Props {
    onNext: () => void;
    onBack: () => void;
  }

  let { onNext, onBack }: Props = $props();

  // Local state for form
  let openaiKey = $state($onboarding.apiKeys.openai);
  let anthropicKey = $state($onboarding.apiKeys.anthropic);
  let showOpenaiKey = $state(false);
  let showAnthropicKey = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let validatingOpenai = $state(false);
  let validatingAnthropic = $state(false);
  let openaiValid = $state<boolean | null>(null);
  let anthropicValid = $state<boolean | null>(null);

  // Check if at least one key is provided
  const canContinue = $derived(
    (openaiKey.trim().length > 0 || anthropicKey.trim().length > 0) && !saving
  );

  // Validate API key format (basic check)
  function validateOpenAIKey(key: string): boolean {
    return key.startsWith("sk-") && key.length > 20;
  }

  function validateAnthropicKey(key: string): boolean {
    return key.length > 20; // Anthropic keys don't have a specific prefix
  }

  async function saveAndContinue() {
    saving = true;
    error = null;
    openaiValid = null;
    anthropicValid = null;

    try {
      // Save OpenAI key if provided
      if (openaiKey.trim()) {
        if (!validateOpenAIKey(openaiKey.trim())) {
          openaiValid = false;
          throw new Error("Invalid OpenAI API key format. Keys should start with 'sk-'");
        }
        validatingOpenai = true;
        await credentialsApi.set("openai", openaiKey.trim());
        openaiValid = true;
        validatingOpenai = false;
      }

      // Save Anthropic key if provided
      if (anthropicKey.trim()) {
        if (!validateAnthropicKey(anthropicKey.trim())) {
          anthropicValid = false;
          throw new Error("Invalid Anthropic API key format.");
        }
        validatingAnthropic = true;
        await credentialsApi.set("anthropic", anthropicKey.trim());
        anthropicValid = true;
        validatingAnthropic = false;
      }

      // Update store
      onboarding.setApiKeys({
        openai: openaiKey.trim(),
        anthropic: anthropicKey.trim()
      });

      // Mark step complete and move on
      onboarding.completeStep();
      onNext();
    } catch (e) {
      error = getErrorMessage(e, "Failed to save API keys");
      onboarding.setError(error);
    } finally {
      saving = false;
      validatingOpenai = false;
      validatingAnthropic = false;
    }
  }

  function handleKeyChange(field: "openai" | "anthropic", value: string) {
    if (field === "openai") {
      openaiKey = value;
      openaiValid = null;
    } else {
      anthropicKey = value;
      anthropicValid = null;
    }
  }
</script>

<div class="max-w-xl mx-auto">
  <!-- Header -->
  <div class="text-center mb-8">
    <h2 class="text-2xl font-bold text-white mb-2">Configure API Keys</h2>
    <p class="text-surface-400">
      Add your AI provider API keys. At least one is required. Keys are encrypted and stored locally.
    </p>
  </div>

  <!-- Error Alert -->
  {#if error}
    <div class="mb-6 p-4 rounded-lg bg-red-900/30 border border-red-800">
      <div class="flex items-start gap-3">
        <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
        <div class="flex-1">
          <p class="text-sm text-red-200">{error}</p>
        </div>
        <button onclick={() => error = null} class="text-red-400 hover:text-red-300">
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>
  {/if}

  <!-- API Key Forms -->
  <div class="space-y-6">
    <!-- OpenAI -->
    <div class="p-4 rounded-lg bg-surface-900 border border-surface-800">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-emerald-600/20 flex items-center justify-center">
          <svg class="w-5 h-5 text-emerald-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-sm font-medium text-white">OpenAI</h3>
          <p class="text-xs text-surface-500">GPT-4, GPT-3.5, and more</p>
        </div>
        {#if openaiValid === true}
          <span class="text-xs text-emerald-400 flex items-center gap-1">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            Saved
          </span>
        {/if}
      </div>
      <div class="relative">
        <input
          type={showOpenaiKey ? "text" : "password"}
          value={openaiKey}
          oninput={(e) => handleKeyChange("openai", e.currentTarget.value)}
          placeholder="sk-..."
          class="w-full px-3 py-2 pr-20 bg-surface-800 border border-surface-700 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-ashwen-500 focus:border-transparent {openaiValid === false ? 'border-red-500' : ''}"
        />
        <button
          type="button"
          onclick={() => showOpenaiKey = !showOpenaiKey}
          class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-surface-400 hover:text-white"
        >
          {showOpenaiKey ? "Hide" : "Show"}
        </button>
      </div>
      <p class="mt-2 text-xs text-surface-500">
        Get your key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" class="text-ashwen-400 hover:underline">platform.openai.com</a>
      </p>
    </div>

    <!-- Anthropic -->
    <div class="p-4 rounded-lg bg-surface-900 border border-surface-800">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-orange-600/20 flex items-center justify-center">
          <svg class="w-5 h-5 text-orange-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.304 3.541l-5.296 15.918h-4.112L2.6 3.541h4.173l3.18 10.08 3.18-10.08h4.171zm4.088 0v15.918h-3.824V3.541h3.824z"/>
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-sm font-medium text-white">Anthropic</h3>
          <p class="text-xs text-surface-500">Claude 3 Opus, Sonnet, Haiku</p>
        </div>
        {#if anthropicValid === true}
          <span class="text-xs text-emerald-400 flex items-center gap-1">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            Saved
          </span>
        {/if}
      </div>
      <div class="relative">
        <input
          type={showAnthropicKey ? "text" : "password"}
          value={anthropicKey}
          oninput={(e) => handleKeyChange("anthropic", e.currentTarget.value)}
          placeholder="Your Anthropic API key..."
          class="w-full px-3 py-2 pr-20 bg-surface-800 border border-surface-700 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-ashwen-500 focus:border-transparent {anthropicValid === false ? 'border-red-500' : ''}"
        />
        <button
          type="button"
          onclick={() => showAnthropicKey = !showAnthropicKey}
          class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-surface-400 hover:text-white"
        >
          {showAnthropicKey ? "Hide" : "Show"}
        </button>
      </div>
      <p class="mt-2 text-xs text-surface-500">
        Get your key from <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" class="text-ashwen-400 hover:underline">console.anthropic.com</a>
      </p>
    </div>
  </div>

  <!-- Info Box -->
  <div class="mt-6 p-4 rounded-lg bg-surface-900/50 border border-surface-800">
    <div class="flex items-start gap-3">
      <svg class="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
      </svg>
      <div>
        <p class="text-sm text-surface-300">
          Your API keys are encrypted using AES-256 and stored locally on your device. 
          They are never sent to our servers.
        </p>
      </div>
    </div>
  </div>

  <!-- Navigation -->
  <div class="flex justify-between items-center mt-8">
    <button
      onclick={onBack}
      disabled={saving}
      class="px-4 py-2 text-sm text-surface-400 hover:text-white transition-colors disabled:opacity-50"
    >
      ← Back
    </button>
    <button
      onclick={saveAndContinue}
      disabled={!canContinue}
      class="px-6 py-2.5 text-sm font-medium bg-ashwen-600 hover:bg-ashwen-500 disabled:bg-surface-700 disabled:text-surface-500 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-ashwen-400 focus:ring-offset-2 focus:ring-offset-surface-950 flex items-center gap-2"
    >
      {#if saving}
        <LoadingSpinner size="sm" />
        Saving...
      {:else}
        Continue
      {/if}
    </button>
  </div>

  <!-- Skip Option -->
  <div class="text-center mt-4">
    <button
      onclick={onNext}
      disabled={saving}
      class="text-xs text-surface-500 hover:text-surface-400 transition-colors"
    >
      Skip for now →
    </button>
  </div>
</div>
