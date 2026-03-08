<script lang="ts">
  import { onboarding } from "$lib/stores/onboarding";

  interface Props {
    onNext: () => void;
  }

  let { onNext }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center min-h-[400px] text-center">
  <!-- Logo/Icon -->
  <div class="mb-8">
    <div class="w-24 h-24 rounded-2xl bg-gradient-to-br from-ashwen-500 to-ashwen-700 flex items-center justify-center shadow-lg shadow-ashwen-900/50">
      <svg class="w-14 h-14 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
      </svg>
    </div>
  </div>

  <!-- Title -->
  <h1 class="text-3xl font-bold text-white mb-4">
    Welcome to Ashwen
  </h1>

  <!-- Description -->
  <p class="text-lg text-surface-400 max-w-md mb-8">
    Your AI-powered development companion. Let's get you set up with your first project and AI assistants.
  </p>

  <!-- Features List -->
  <div class="grid gap-4 max-w-md mb-8 text-left">
    <div class="flex items-start gap-3 p-3 rounded-lg bg-surface-900/50">
      <div class="w-8 h-8 rounded-lg bg-ashwen-600/20 flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4 text-ashwen-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>
      </div>
      <div>
        <h3 class="text-sm font-medium text-white">Multiple AI Providers</h3>
        <p class="text-xs text-surface-500">Use OpenAI, Anthropic, or local models with Ollama</p>
      </div>
    </div>

    <div class="flex items-start gap-3 p-3 rounded-lg bg-surface-900/50">
      <div class="w-8 h-8 rounded-lg bg-ashwen-600/20 flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4 text-ashwen-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
      </div>
      <div>
        <h3 class="text-sm font-medium text-white">Agent Teams</h3>
        <p class="text-xs text-surface-500">Collaborate with specialized AI agents</p>
      </div>
    </div>

    <div class="flex items-start gap-3 p-3 rounded-lg bg-surface-900/50">
      <div class="w-8 h-8 rounded-lg bg-ashwen-600/20 flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4 text-ashwen-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <div>
        <h3 class="text-sm font-medium text-white">Persistent Memory</h3>
        <p class="text-xs text-surface-500">Agents remember your project context</p>
      </div>
    </div>
  </div>

  <!-- Get Started Button -->
  <button
    onclick={onNext}
    class="px-8 py-3 text-lg font-medium bg-ashwen-600 hover:bg-ashwen-500 text-white rounded-lg transition-colors shadow-lg shadow-ashwen-900/30 focus:outline-none focus:ring-2 focus:ring-ashwen-400 focus:ring-offset-2 focus:ring-offset-surface-950"
  >
    Get Started
  </button>

  <p class="mt-4 text-xs text-surface-600">
    Setup takes about 2 minutes
  </p>
</div>
