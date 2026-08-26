<script lang="ts">
  interface Props {
    online?: boolean;
    /** Agent / telemetry status */
    status?: "pending" | "running" | "done" | "iterating" | "error" | "idle";
    pulse?: boolean;
    size?: "sm" | "md";
    class?: string;
  }

  let {
    online = false,
    status,
    pulse = false,
    size = "sm",
    class: className = "",
  }: Props = $props();

  const resolved = $derived.by(() => {
    if (status) return status;
    if (online) return "done";
    return "idle";
  });

  const shouldPulse = $derived(pulse || resolved === "running");
</script>

<span
  class="status-dot size-{size} st-{resolved} {className}"
  class:pulse={shouldPulse}
  aria-hidden="true"
></span>

<style>
  .status-dot {
    display: inline-block;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--status-pending);
  }

  .size-sm {
    width: 6px;
    height: 6px;
  }

  .size-md {
    width: 8px;
    height: 8px;
  }

  .st-idle,
  .st-pending {
    background: var(--status-pending);
  }

  .st-running {
    background: var(--status-running);
  }

  .st-done {
    background: var(--status-done);
  }

  .st-iterating {
    background: var(--status-iterating);
  }

  .st-error {
    background: var(--status-error);
  }

  .pulse {
    animation: pulse-live 1.4s ease-in-out infinite;
  }
</style>
