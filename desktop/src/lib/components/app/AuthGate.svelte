<script lang="ts">
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { formatAuthError, saveContinueLocal } from "$lib/auth/auth-prefs";

  interface Props {
    onDone: () => void;
  }

  let { onDone }: Props = $props();

  let mode = $state<"signin" | "register">("signin");
  let email = $state("");
  let password = $state("");
  let busy = $state(false);
  let error = $state("");

  async function submit() {
    if (!email.trim() || password.length < 8) {
      error = "Use a valid email and a password of at least 8 characters.";
      return;
    }
    busy = true;
    error = "";
    try {
      if (mode === "register") {
        await api.cloudWatchRegister(email.trim(), password);
      } else {
        await api.cloudWatchLogin(email.trim(), password);
      }
      saveContinueLocal(false);
      await connection.refreshStatus();
      onDone();
    } catch (e) {
      error = formatAuthError(e, mode === "register" ? "Could not create account" : "Could not sign in");
    } finally {
      busy = false;
    }
  }

  function continueLocal() {
    saveContinueLocal(true);
    onDone();
  }
</script>

<div class="gate" role="dialog" aria-modal="true" aria-labelledby="auth-title">
  <div class="card">
    <p class="brand">Nous</p>
    <h1 id="auth-title">{mode === "signin" ? "Sign in" : "Create account"}</h1>
    <p class="sub">
      One account for Cloud Watch morning briefs. Uses your Models API key automatically.
      Notes stay on this Mac.
    </p>

    <label class="field">
      <span>Email</span>
      <input type="email" bind:value={email} autocomplete="username" disabled={busy} />
    </label>
    <label class="field">
      <span>Password</span>
      <input
        type="password"
        bind:value={password}
        autocomplete={mode === "register" ? "new-password" : "current-password"}
        disabled={busy}
      />
    </label>

    {#if error}
      <p class="err" role="alert">{error}</p>
    {/if}

    <button type="button" class="primary" disabled={busy} onclick={() => void submit()}>
      {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
    </button>

    <button
      type="button"
      class="link"
      disabled={busy}
      onclick={() => {
        mode = mode === "signin" ? "register" : "signin";
        error = "";
      }}
    >
      {mode === "signin" ? "Need an account? Create one" : "Already have an account? Sign in"}
    </button>

    <button type="button" class="ghost" disabled={busy} onclick={continueLocal}>
      Continue without account
    </button>
    <p class="hint">Local Teach, Ask, Research, and Watch catch-up still work offline.</p>
  </div>
</div>

<style>
  .gate {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: grid;
    place-items: center;
    padding: 1.5rem;
    background: color-mix(in srgb, var(--bg) 88%, transparent);
  }
  .card {
    width: min(24rem, 100%);
    padding: 1.5rem 1.35rem 1.25rem;
    border-radius: var(--radius-2xl, 16px);
    border: 1px solid var(--border);
    background: var(--paper, var(--bg-elevated));
    box-shadow: none;
  }
  .brand {
    margin: 0;
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
  h1 {
    margin: 0.35rem 0 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
  }
  .sub {
    margin: 0.4rem 0 1.1rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.45;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-bottom: 0.65rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
  input {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    color: var(--text);
    font: inherit;
    padding: 0.45rem 0.6rem;
  }
  .err {
    margin: 0 0 0.65rem;
    font-size: var(--text-sm);
    color: var(--error);
  }
  .primary,
  .ghost,
  .link {
    width: 100%;
    font: inherit;
    font-size: var(--text-sm);
    cursor: pointer;
    border-radius: var(--radius-full);
    padding: 0.45rem 0.85rem;
  }
  .primary {
    border: none;
    background: var(--text);
    color: var(--bg-elevated);
    font-weight: var(--font-semibold);
    margin-top: 0.25rem;
  }
  .primary:disabled,
  .ghost:disabled,
  .link:disabled {
    opacity: 0.5;
    cursor: wait;
  }
  .link {
    margin-top: 0.55rem;
    border: none;
    background: transparent;
    color: var(--accent-link);
  }
  .ghost {
    margin-top: 0.35rem;
    border: 1px solid var(--border);
    background: var(--control-fill);
    color: var(--text-muted);
  }
  .hint {
    margin: 0.55rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
    text-align: center;
    line-height: 1.4;
  }
</style>
