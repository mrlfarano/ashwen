<script lang="ts">
  import { onboarding, progress, currentStepIndex, totalSteps } from "$lib/stores/onboarding";
  import type { OnboardingStep } from "$lib/stores/onboarding";

  interface StepInfo {
    id: OnboardingStep;
    label: string;
    shortLabel: string;
  }

  const steps: StepInfo[] = [
    { id: "welcome", label: "Welcome", shortLabel: "1" },
    { id: "api-keys", label: "API Keys", shortLabel: "2" },
    { id: "local-model", label: "Local Model", shortLabel: "3" },
    { id: "create-project", label: "Create Project", shortLabel: "4" },
    { id: "complete", label: "Complete", shortLabel: "5" }
  ];

  function getStepStatus(stepId: OnboardingStep): "completed" | "current" | "upcoming" {
    if ($onboarding.completedSteps.includes(stepId)) return "completed";
    if ($onboarding.currentStep === stepId) return "current";
    return "upcoming";
  }

  function getStepClasses(status: "completed" | "current" | "upcoming"): string {
    switch (status) {
      case "completed":
        return "bg-ashwen-600 border-ashwen-500 text-white";
      case "current":
        return "bg-ashwen-600 border-ashwen-400 text-white ring-2 ring-ashwen-400 ring-offset-2 ring-offset-surface-950";
      default:
        return "bg-surface-800 border-surface-700 text-surface-500";
    }
  }

  function getConnectorClasses(stepIndex: number): string {
    if (stepIndex < $onboarding.completedSteps.length) {
      return "bg-ashwen-600";
    }
    return "bg-surface-700";
  }
</script>

<div class="w-full" role="navigation" aria-label="Onboarding progress">
  <!-- Mobile Progress Bar -->
  <div class="sm:hidden mb-6">
    <div class="flex justify-between items-center mb-2">
      <span class="text-sm text-surface-400">
        Step {$currentStepIndex + 1} of {totalSteps}
      </span>
      <span class="text-sm font-medium text-ashwen-400">{$progress}%</span>
    </div>
    <div class="h-2 bg-surface-800 rounded-full overflow-hidden">
      <div 
        class="h-full bg-ashwen-600 transition-all duration-300 ease-out"
        style="width: {$progress}%"
      ></div>
    </div>
  </div>

  <!-- Desktop Step Indicators -->
  <div class="hidden sm:block">
    <div class="flex items-center justify-between mb-2">
      {#each steps as step, index}
        <div class="flex items-center flex-1">
          <!-- Step Circle -->
          <button
            onclick={() => {
              if ($onboarding.completedSteps.includes(step.id)) {
                onboarding.goToStep(step.id);
              }
            }}
            disabled={!$onboarding.completedSteps.includes(step.id) && step.id !== $onboarding.currentStep}
            class="relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-200 {getStepClasses(getStepStatus(step.id))} {$onboarding.completedSteps.includes(step.id) ? 'cursor-pointer hover:scale-105' : 'cursor-default'}"
            aria-current={getStepStatus(step.id) === "current" ? "step" : undefined}
            aria-label="{step.label} - {getStepStatus(step.id)}"
          >
            {#if getStepStatus(step.id) === "completed"}
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            {:else}
              <span class="text-sm font-semibold">{step.shortLabel}</span>
            {/if}
          </button>

          <!-- Connector Line -->
          {#if index < steps.length - 1}
            <div class="flex-1 mx-2 h-0.5 rounded-full transition-colors duration-300 {getConnectorClasses(index)}"></div>
          {/if}
        </div>
      {/each}
    </div>

    <!-- Step Labels -->
    <div class="flex justify-between">
      {#each steps as step, index}
        <div class="flex-1 text-center">
          <span 
            class="text-xs font-medium {getStepStatus(step.id) === "current" ? "text-ashwen-400" : getStepStatus(step.id) === "completed" ? "text-surface-300" : "text-surface-600"}"
          >
            {step.label}
          </span>
        </div>
      {/each}
    </div>
  </div>
</div>
