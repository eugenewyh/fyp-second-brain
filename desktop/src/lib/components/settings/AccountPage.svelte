<script lang="ts">
  import { onMount } from "svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import {
    authConfigured,
    currentUser,
    deleteAccount,
    formatAuthClientError,
    sendCode,
    signOut,
    verifyCode,
  } from "$lib/auth/client";
  import { getDeviceName, getStoredEmail } from "$lib/auth/session";
  import { authSession } from "$lib/auth/auth-session.svelte";

  type Step = "email" | "otp" | "signed-in";

  let step = $state<Step>("email");
  let email = $state("");
  let otp = $state("");
  let displayName = $state("");
  let showName = $state(false);
  let busy = $state(false);
  let error = $state("");
  let hint = $state("");
  let userEmail = $state("");
  let deviceName = $state(getDeviceName());
  let otpAttempts = $state(0);

  async function refreshSession() {
    authSession.hydrate();
    if (!authSession.signedIn) {
      step = "email";
      userEmail = "";
      return;
    }
    try {
      const sess = await currentUser();
      const u = sess.data?.user;
      if (u?.email) {
        userEmail = u.email;
        step = "signed-in";
        return;
      }
    } catch {
      /* fall through */
    }
    userEmail = authSession.email || getStoredEmail() || "Signed in";
    step = "signed-in";
  }

  onMount(() => {
    void refreshSession();
  });

  function onOtpInput(e: Event) {
    const el = e.currentTarget as HTMLInputElement;
    otp = el.value.replace(/\D/g, "").slice(0, 6);
  }

  async function onContinueEmail() {
    const e = email.trim().toLowerCase();
    if (!e || !e.includes("@")) {
      error = "Enter a valid email address.";
      return;
    }
    if (!authConfigured()) {
      error = "Account sign-in is not configured on this build (VITE_AUTH_URL).";
      return;
    }
    busy = true;
    error = "";
    hint = "";
    try {
      const res = await sendCode(e);
      if (res.error) {
        error = formatAuthClientError(res.error, "Could not send code");
        return;
      }
      email = e;
      otp = "";
      otpAttempts = 0;
      step = "otp";
      hint = "Check your email for a 6-digit code. Locally, the code is also in the auth server log.";
    } catch (err) {
      error = err instanceof Error ? err.message : "Could not send code";
    } finally {
      busy = false;
    }
  }

  async function onVerify() {
    if (otpAttempts >= 3) {
      error = "Too many attempts. Request a new code.";
      return;
    }
    if (!/^\d{6}$/.test(otp.trim())) {
      error = "Enter the 6-digit code.";
      return;
    }
    busy = true;
    error = "";
    try {
      const res = await verifyCode(email, otp, showName ? displayName : undefined);
      if (res.error) {
        otpAttempts += 1;
        error = formatAuthClientError(res.error, "Invalid or expired code");
        if (otpAttempts >= 3) {
          error = "Too many attempts. Request a new code.";
        }
        return;
      }
      await refreshSession();
      await connection.refreshStatus();
      hint = "";
    } catch (err) {
      otpAttempts += 1;
      error = err instanceof Error ? err.message : "Could not verify code";
    } finally {
      busy = false;
    }
  }

  async function onSignOut() {
    busy = true;
    error = "";
    try {
      await signOut();
      email = "";
      otp = "";
      step = "email";
      userEmail = "";
      await connection.refreshStatus();
    } catch (err) {
      error = err instanceof Error ? err.message : "Could not sign out";
    } finally {
      busy = false;
    }
  }

  async function onDelete() {
    if (!confirm("Delete this account on the auth server? Notes on this Mac stay local.")) {
      return;
    }
    busy = true;
    error = "";
    try {
      const res = await deleteAccount();
      if (res.note) hint = res.note;
      email = "";
      otp = "";
      step = "email";
      userEmail = "";
      await connection.refreshStatus();
    } catch (err) {
      error = err instanceof Error ? err.message : "Could not delete account";
    } finally {
      busy = false;
    }
  }
</script>

<section class="account">
  <div class="st-card">
    <div class="st-card-head">
      <h3 class="st-card-title">Account</h3>
      <p class="st-card-sub">
        One email code for sign-up and sign-in. Notes stay on this Mac whether you are signed in or
        not. Cloud Scheduled Research uses this account when the Mac is asleep.
      </p>
    </div>

    {#if step === "signed-in"}
      <p class="row"><span class="label">Email</span> {userEmail}</p>
      <p class="row"><span class="label">Device</span> {deviceName}</p>
      {#if connection.cloudWatchAvailable}
        <p class="row muted">
          Cloud Scheduled Research: {connection.cloudWatchConfigured
            ? connection.cloudWatchHasKey
              ? "connected (Models key on server)"
              : "connected — sync Models key from Settings → Models"
            : "sign-in synced; open Scheduled Research to sync active schedules"}
        </p>
      {/if}
      <div class="actions">
        <button type="button" class="ghost" disabled={busy} onclick={() => void onSignOut()}>
          Sign out
        </button>
        <button type="button" class="danger" disabled={busy} onclick={() => void onDelete()}>
          Delete account
        </button>
      </div>
    {:else if step === "email"}
      <label class="st-field">
        <span class="st-field-label">Email</span>
        <input
          class="st-control"
          type="email"
          bind:value={email}
          autocomplete="username"
          disabled={busy}
          placeholder="you@example.com"
        />
      </label>
      <button type="button" class="primary" disabled={busy} onclick={() => void onContinueEmail()}>
        {busy ? "Sending…" : "Continue"}
      </button>
    {:else}
      <p class="muted">Code sent to <strong>{email}</strong></p>
      <label class="st-field">
        <span class="st-field-label">6-digit code</span>
        <input
          class="st-control otp"
          type="text"
          inputmode="numeric"
          maxlength="6"
          pattern="[0-9]*"
          value={otp}
          autocomplete="one-time-code"
          disabled={busy || otpAttempts >= 3}
          placeholder="000000"
          oninput={onOtpInput}
        />
      </label>
      <label class="name-opt">
        <input class="name-opt-box" type="checkbox" bind:checked={showName} disabled={busy} />
        <span class="name-opt-text">I'm new — set a display name</span>
      </label>
      {#if showName}
        <label class="st-field">
          <span class="st-field-label">Display name</span>
          <input
            class="st-control"
            type="text"
            bind:value={displayName}
            disabled={busy}
            maxlength="80"
          />
        </label>
      {/if}
      <div class="actions">
        <button
          type="button"
          class="primary"
          disabled={busy || otpAttempts >= 3}
          onclick={() => void onVerify()}
        >
          {busy ? "Verifying…" : "Verify"}
        </button>
        <button
          type="button"
          class="ghost"
          disabled={busy}
          onclick={() => {
            step = "email";
            otp = "";
            error = "";
            otpAttempts = 0;
          }}
        >
          Back
        </button>
      </div>
      {#if otpAttempts >= 3}
        <button
          type="button"
          class="link"
          disabled={busy}
          onclick={() => {
            otpAttempts = 0;
            void onContinueEmail();
          }}
        >
          Request a new code
        </button>
      {/if}
    {/if}

    {#if error}
      <p class="err" role="alert">{error}</p>
    {/if}
    {#if hint}
      <p class="st-hint">{hint}</p>
    {/if}
  </div>
</section>

<style>
  .account {
    max-width: 28rem;
  }

  .st-field {
    margin-bottom: 0.85rem;
  }

  .otp {
    font-family: var(--font-mono, ui-monospace, monospace);
    font-size: var(--text-lg, 1.125rem);
    letter-spacing: 0.35em;
    text-align: left;
  }

  /* Global app.css sets input { width: 100% } — that breaks checkboxes in a flex row. */
  .name-opt {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.55rem;
    margin: 0.15rem 0 0.85rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    max-width: 100%;
  }

  .name-opt-box {
    width: 1rem !important;
    min-width: 1rem;
    max-width: 1rem;
    height: 1rem;
    margin: 0;
    padding: 0;
    flex-shrink: 0;
    accent-color: var(--text);
  }

  .name-opt-text {
    flex: 1 1 auto;
    min-width: 0;
    line-height: 1.4;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  .primary,
  .ghost,
  .danger,
  .link {
    font: inherit;
    font-size: var(--text-sm);
    cursor: pointer;
    border-radius: var(--radius-full);
    padding: 0.4rem 0.85rem;
  }

  .primary {
    border: none;
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    font-weight: var(--font-semibold);
  }

  .ghost {
    border: 1px solid var(--border);
    background: var(--control-fill);
    color: var(--text-muted);
  }

  .danger {
    border: 1px solid var(--border);
    background: transparent;
    color: var(--error, #b33);
  }

  .link {
    margin-top: 0.5rem;
    border: none;
    background: transparent;
    color: var(--accent-link);
  }

  .primary:disabled,
  .ghost:disabled,
  .danger:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  .row {
    margin: 0.35rem 0;
    font-size: var(--text-sm);
  }

  .label {
    color: var(--text-faint);
    margin-right: 0.35rem;
  }

  .muted {
    color: var(--text-muted);
    font-size: var(--text-sm);
    margin: 0 0 0.75rem;
  }

  .err {
    margin: 0.65rem 0 0;
    font-size: var(--text-sm);
    color: var(--error);
  }
</style>
