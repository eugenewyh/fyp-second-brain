<script lang="ts">
  interface Props {
    time?: string;
    agent?: string;
    message: string;
    tone?: "default" | "live" | "success" | "warning" | "error";
    class?: string;
  }

  let {
    time = "",
    agent = "",
    message,
    tone = "default",
    class: className = "",
  }: Props = $props();
</script>

<div class="log-line tone-{tone} {className}">
  {#if time}
    <span class="time">{time}</span>
  {/if}
  {#if agent}
    <span class="agent">{agent}</span>
  {/if}
  <span class="msg">{message}</span>
</div>

<style>
  .log-line {
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 0.5rem;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    line-height: 1.45;
    padding: 0.15rem 0;
    color: var(--text-muted);
  }

  .time {
    color: var(--text-faint);
    min-width: 4.5rem;
  }

  .agent {
    color: var(--accent-link);
    min-width: 5rem;
    font-weight: var(--font-medium);
  }

  .msg {
    color: var(--text-muted);
    word-break: break-word;
  }

  .tone-live .msg {
    color: var(--text);
  }

  .tone-success .msg {
    color: var(--success);
  }

  .tone-warning .msg {
    color: var(--warning);
  }

  .tone-error .msg {
    color: var(--error);
  }
</style>
