/**
 * Onboarding Store - Manages first-run wizard state
 */

import { writable, derived } from "svelte/store";

// Onboarding step types
export type OnboardingStep = 
  | "welcome"
  | "api-keys"
  | "local-model"
  | "create-project"
  | "complete";

// API key configuration
export interface ApiKeyConfig {
  openai: string;
  anthropic: string;
}

// Local model configuration
export interface LocalModelConfig {
  provider: "ollama" | "lm-studio" | "none";
  model: string;
  endpoint: string;
}

// Project configuration
export interface ProjectConfig {
  name: string;
  path: string;
  description: string;
}

// Onboarding state
export interface OnboardingState {
  currentStep: OnboardingStep;
  completedSteps: OnboardingStep[];
  
  // Step data
  apiKeys: ApiKeyConfig;
  localModel: LocalModelConfig;
  project: ProjectConfig;
  
  // Status
  isSubmitting: boolean;
  error: string | null;
  
  // First-run flag
  isFirstRun: boolean;
}

// All steps in order
export const ONBOARDING_STEPS: OnboardingStep[] = [
  "welcome",
  "api-keys",
  "local-model",
  "create-project",
  "complete"
];

// Step indices for progress calculation
const STEP_INDICES: Record<OnboardingStep, number> = {
  "welcome": 0,
  "api-keys": 1,
  "local-model": 2,
  "create-project": 3,
  "complete": 4
};

// Default state
const defaultState: OnboardingState = {
  currentStep: "welcome",
  completedSteps: [],
  apiKeys: {
    openai: "",
    anthropic: ""
  },
  localModel: {
    provider: "none",
    model: "",
    endpoint: ""
  },
  project: {
    name: "",
    path: "",
    description: ""
  },
  isSubmitting: false,
  error: null,
  isFirstRun: true
};

function createOnboardingStore() {
  const { subscribe, set, update } = writable<OnboardingState>(defaultState);

  return {
    subscribe,
    
    // Reset to initial state
    reset: () => set(defaultState),
    
    // Set first-run status
    setFirstRun: (isFirstRun: boolean) => 
      update((s) => ({ ...s, isFirstRun })),
    
    // Navigate to a specific step
    goToStep: (step: OnboardingStep) => 
      update((s) => ({ ...s, currentStep: step, error: null })),
    
    // Go to next step
    nextStep: () => 
      update((s) => {
        const currentIndex = STEP_INDICES[s.currentStep];
        const nextIndex = currentIndex + 1;
        if (nextIndex < ONBOARDING_STEPS.length) {
          const nextStep = ONBOARDING_STEPS[nextIndex];
          return {
            ...s,
            currentStep: nextStep,
            completedSteps: [...s.completedSteps, s.currentStep],
            error: null
          };
        }
        return s;
      }),
    
    // Go to previous step
    prevStep: () => 
      update((s) => {
        const currentIndex = STEP_INDICES[s.currentStep];
        const prevIndex = currentIndex - 1;
        if (prevIndex >= 0) {
          return {
            ...s,
            currentStep: ONBOARDING_STEPS[prevIndex],
            error: null
          };
        }
        return s;
      }),
    
    // Mark current step as complete and advance
    completeStep: () => 
      update((s) => ({
        ...s,
        completedSteps: [...s.completedSteps, s.currentStep],
        error: null
      })),
    
    // Update API keys
    setApiKeys: (keys: Partial<ApiKeyConfig>) => 
      update((s) => ({ ...s, apiKeys: { ...s.apiKeys, ...keys } })),
    
    // Update local model config
    setLocalModel: (config: Partial<LocalModelConfig>) => 
      update((s) => ({ ...s, localModel: { ...s.localModel, ...config } })),
    
    // Update project config
    setProject: (project: Partial<ProjectConfig>) => 
      update((s) => ({ ...s, project: { ...s.project, ...project } })),
    
    // Set submitting state
    setSubmitting: (isSubmitting: boolean) => 
      update((s) => ({ ...s, isSubmitting })),
    
    // Set error
    setError: (error: string | null) => 
      update((s) => ({ ...s, error, isSubmitting: false })),
    
    // Mark onboarding as complete
    markComplete: () => 
      update((s) => ({
        ...s,
        currentStep: "complete",
        completedSteps: ONBOARDING_STEPS,
        isSubmitting: false,
        error: null
      }))
  };
}

export const onboarding = createOnboardingStore();

// Derived stores for convenience
export const currentStepIndex = derived(onboarding, ($onboarding) => 
  STEP_INDICES[$onboarding.currentStep]
);

export const totalSteps = ONBOARDING_STEPS.length;

export const progress = derived(onboarding, ($onboarding) => {
  const current = STEP_INDICES[$onboarding.currentStep];
  return Math.round((current / (totalSteps - 1)) * 100);
});

export const canGoBack = derived(onboarding, ($onboarding) => 
  $onboarding.currentStep !== "welcome" && $onboarding.currentStep !== "complete"
);

export const canGoNext = derived(onboarding, ($onboarding) => {
  // Add validation logic per step if needed
  return $onboarding.currentStep !== "complete";
});
