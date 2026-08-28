<script lang="ts">
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { signOut } from "$lib/auth/client";

  interface Props {
    settingsForm: Record<string, string>;
    saving: boolean;
    onPersist: (partial: Record<string, string>) => void;
  }

  let { settingsForm, saving, onPersist }: Props = $props();

  let mcpStatus = $state<{
    enabled: boolean;
    configured: boolean;
    ok: boolean;
    error: string;
  } | null>(null);

  const enabled = $derived((settingsForm.ENABLE_MCP || "false") === "true");

  const badge = $derived.by(() => {
    if (!enabled) return "Off";
    if (!(settingsForm.NOTION_API_KEY || "").trim()) return "Missing token";
    if (!mcpStatus) return "Checking";
    if (mcpStatus.ok) return "Connected";
    if (mcpStatus.error) return "Error";
    return "Off";
  });

  async function refreshStatus() {
    try {
      mcpStatus = await api.mcpStatus();
    } catch {
      mcpStatus = { enabled, configured: false, ok: false, error: "Couldn't reach sidecar" };
    }
  }

  $effect(() => {
    void settingsForm.ENABLE_MCP;
    void settingsForm.NOTION_API_KEY;
    void refreshStatus();
  });

  function onEnable(e: Event) {
    onPersist({ ENABLE_MCP: (e.currentTarget as HTMLSelectElement).value });
  }

  function onTokenBlur(e: FocusEvent) {
    onPersist({ NOTION_API_KEY: (e.currentTarget as HTMLInputElement).value });
  }

  let cwBusy = $state(false);
  let cwMsg = $state("");
  let cwErr = $state(false);

  $effect(() => {
    void connection.cloudWatchConfigured;
    void connection.cloudWatchHasKey;
  });

  async function cwSyncKey() {
    cwBusy = true;
    cwMsg = "";
    cwErr = false;
    try {
      await api.cloudWatchSyncLlm();
      cwMsg = "Models key synced to Cloud Scheduled Research.";
      await connection.refreshStatus();
    } catch (e) {
      cwErr = true;
      cwMsg = e instanceof Error ? e.message : "Could not sync key";
    } finally {
      cwBusy = false;
    }
  }

  async function cwLogout() {
    cwBusy = true;
    try {
      await signOut();
      cwMsg = "Signed out.";
      await connection.refreshStatus();
    } catch (e) {
      cwErr = true;
      cwMsg = e instanceof Error ? e.message : "Could not sign out";
    } finally {
      cwBusy = false;
    }
  }
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Connectors</h3>
    <p class="st-card-sub">
      Optional sources the agent can read during research. Off by default — your vault stays local.
    </p>
  </div>

  <ul class="rows">
    <li class="row">
      <div class="left">
        <span class="mono">No</span>
        <div class="copy">
          <div class="name-row">
            <span class="name">Notion</span>
            <span class="badge" class:ok={badge === "Connected"}>{badge}</span>
          </div>
          <p class="desc">
            Create an internal integration, share pages with it, then paste the token. Read-only;
            used on hybrid research only.
          </p>
        </div>
      </div>
    </li>
    <li class="row later">
      <div class="left">
        <span class="mono dim">Dr</span>
        <div>
          <div class="name-row">
            <span class="name">Google Drive</span>
            <span class="badge">Later</span>
          </div>
          <p class="desc">After Notion.</p>
        </div>
      </div>
    </li>
  </ul>

  <div class="st-field-grid fields">
    <label class="st-field">
      <span class="st-field-label">Notion</span>
      <select
        class="st-control"
        value={settingsForm.ENABLE_MCP || "false"}
        onchange={onEnable}
        disabled={saving}
      >
        <option value="false">Off</option>
        <option value="true">On</option>
      </select>
    </label>
    <label class="st-field">
      <span class="st-field-label">Integration token</span>
      <input
        class="st-control"
        type="password"
        value={settingsForm.NOTION_API_KEY ?? ""}
        placeholder="ntn_… or secret_…"
        autocomplete="off"
        disabled={saving}
        onblur={onTokenBlur}
      />
    </label>
  </div>

  {#if mcpStatus?.error && enabled}
    <p class="st-msg error">{mcpStatus.error}</p>
  {/if}

  <p class="st-hint">Connecting a source lets the agent read it during research.</p>
</section>

{#if connection.cloudWatchAvailable}
  <section class="st-card" style="margin-top: 1rem">
    <div class="st-card-head">
      <h3 class="st-card-title">Cloud Scheduled Research</h3>
      <p class="st-card-sub">
        Morning briefs while this Mac is asleep. Uses the same LLM key as Settings → Models
        (synced to the server for the 9am job). Notes stay on this device.
      </p>
    </div>

    <p class="status-line">
      {#if connection.cloudWatchConfigured}
        Signed in as {connection.cloudWatchEmail || "…"}
        {connection.cloudWatchHasKey
          ? " · Models key on server"
          : " · Models key not synced yet — add a key in Models, or Sync now"}
      {:else}
        Not signed in — use Settings → Account (email code). Notes stay local either way.
        <button type="button" class="linkish" onclick={() => app.openSettings("account")}>
          Open Account
        </button>
      {/if}
    </p>

    {#if connection.cloudWatchConfigured}
      <div class="cw-actions">
        <button type="button" class="st-btn" disabled={cwBusy} onclick={() => void cwSyncKey()}>
          Sync Models key
        </button>
        <button type="button" class="st-btn ghost" disabled={cwBusy} onclick={() => void cwLogout()}>
          Sign out
        </button>
      </div>
    {/if}

    {#if cwMsg}
      <p class="st-msg" class:error={cwErr}>{cwMsg}</p>
    {/if}
  </section>
{/if}

<style>
  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
    background: var(--bg-elevated);
  }

  .row {
    display: flex;
    align-items: center;
    padding: 0.75rem 0.85rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .row:last-child {
    border-bottom: none;
  }

  .row.later {
    opacity: 0.55;
  }

  .left {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    min-width: 0;
  }

  .copy {
    min-width: 0;
  }

  .mono {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    font-family: var(--font-mono);
    background: color-mix(in srgb, var(--accent-live) 22%, var(--surface));
    color: var(--accent-link);
  }

  .mono.dim {
    background: var(--surface);
    color: var(--text-faint);
  }

  .name-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .name {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .desc {
    margin: 0.15rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .badge {
    font-size: var(--text-2xs);
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xs);
    padding: 0.1rem 0.35rem;
  }

  .badge.ok {
    color: var(--accent-link);
    background: var(--accent-live-dim);
    border-color: transparent;
  }

  .fields {
    margin-top: 0.85rem;
  }

  .status-line {
    margin: 0.35rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .linkish {
    display: inline;
    margin-left: 0.25rem;
    border: none;
    background: none;
    padding: 0;
    font: inherit;
    font-size: inherit;
    color: var(--accent-link);
    cursor: pointer;
    text-decoration: underline;
  }

  .cw-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .st-btn {
    border: none;
    border-radius: var(--radius-md);
    padding: 0.4rem 0.85rem;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    background: var(--text);
    color: var(--bg-elevated);
    cursor: pointer;
  }

  .st-btn.ghost {
    background: var(--control-fill);
    color: var(--text);
    border: 1px solid var(--border);
  }

  .st-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
