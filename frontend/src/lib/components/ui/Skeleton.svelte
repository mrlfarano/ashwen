<script lang="ts">
  interface Props {
    /** Width of the skeleton - can be any CSS width value */
    width?: string;
    /** Height of the skeleton - can be any CSS height value */
    height?: string;
    /** Variant for border radius */
    variant?: "text" | "rectangular" | "circular";
    /** Number of skeleton lines to render */
    lines?: number;
    /** Gap between lines when lines > 1 */
    gap?: string;
    /** Additional CSS classes */
    class?: string;
  }

  let {
    width = "100%",
    height = "1rem",
    variant = "rectangular",
    lines = 1,
    gap = "0.5rem",
    class: className = "",
  }: Props = $props();

  const variantClasses = {
    text: "rounded",
    rectangular: "rounded-lg",
    circular: "rounded-full",
  };

  function getLineStyle(index: number, total: number): string {
    // Last line is typically shorter for visual variety
    if (index === total - 1 && total > 1) {
      return `width: 75%; height: ${height};`;
    }
    return `width: ${width}; height: ${height};`;
  }
</script>

{#if lines === 1}
  <div
    class="animate-pulse bg-surface-800 {variantClasses[variant]} {className}"
    style="width: {width}; height: {height};"
    aria-hidden="true"
  ></div>
{:else}
  <div class="flex flex-col" style="gap: {gap};">
    {#each Array(lines) as _, i}
      <div
        class="animate-pulse bg-surface-800 {variantClasses[variant]} {className}"
        style={getLineStyle(i, lines)}
        aria-hidden="true"
      ></div>
    {/each}
  </div>
{/if}
