<script lang="ts">
  interface Props {
    width?: string;
    height?: string;
    class?: string;
  }

  let {
    width = "100%",
    height = "0.75rem",
    class: className = "",
  }: Props = $props();
</script>

<span
  class="skeleton {className}"
  style:width
  style:height
  aria-hidden="true"
></span>

<style>
  .skeleton {
    display: inline-block;
    border-radius: var(--radius-sm);
    background: linear-gradient(
      90deg,
      var(--surface) 0%,
      var(--surface-hover) 50%,
      var(--surface) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.2s ease-in-out infinite;
  }

  @keyframes shimmer {
    0% {
      background-position: 100% 0;
    }
    100% {
      background-position: -100% 0;
    }
  }
</style>
