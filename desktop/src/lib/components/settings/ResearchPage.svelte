<script lang="ts">
  interface Props {
    settingsForm: Record<string, string>;
    saving: boolean;
    onPersist: (partial: Record<string, string>) => void;
  }

  let { settingsForm, saving, onPersist }: Props = $props();

  let showAdvanced = $state(false);

  function onSelect(key: string) {
    return (e: Event) => {
      onPersist({ [key]: (e.currentTarget as HTMLSelectElement).value });
    };
  }

  function onBlur(key: string) {
    return (e: FocusEvent) => {
      onPersist({ [key]: (e.currentTarget as HTMLInputElement).value });
    };
  }
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Search sources</h3>
    <p class="st-card-sub">Beyond your vault for hybrid / web research.</p>
  </div>
  <div class="st-field-grid">
    <label class="st-field">
      <span class="st-field-label">Web search</span>
      <select
        class="st-control"
        value={settingsForm.ENABLE_WEB_SEARCH}
        onchange={onSelect("ENABLE_WEB_SEARCH")}
        disabled={saving}
      >
        <option value="true">On</option>
        <option value="false">Off</option>
      </select>
    </label>
    <label class="st-field">
      <span class="st-field-label">Academic papers (arXiv)</span>
      <select
        class="st-control"
        value={settingsForm.ENABLE_ARXIV}
        onchange={onSelect("ENABLE_ARXIV")}
        disabled={saving}
      >
        <option value="true">On</option>
        <option value="false">Off</option>
      </select>
    </label>
    <label class="st-field st-field-span">
      <span class="st-field-label">Tavily API key <span class="st-opt">optional</span></span>
      <input
        class="st-control"
        type="password"
        value={settingsForm.TAVILY_API_KEY}
        placeholder="tvly-…"
        autocomplete="off"
        disabled={saving}
        onblur={onBlur("TAVILY_API_KEY")}
      />
    </label>
  </div>
</section>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Harness budget</h3>
    <p class="st-card-sub">After you set a goal or an active schedule, Nous runs inside these limits without asking again.</p>
  </div>
  <div class="st-field-grid">
    <label class="st-field">
      <span class="st-field-label">Max goal passes</span>
      <input
        class="st-control narrow"
        value={settingsForm.MAX_GOAL_PASSES}
        placeholder="2"
        disabled={saving}
        onblur={onBlur("MAX_GOAL_PASSES")}
      />
    </label>
    <label class="st-field">
      <span class="st-field-label">Max scheduled research passes</span>
      <input
        class="st-control narrow"
        value={settingsForm.WATCH_MAX_PASSES}
        placeholder="1"
        disabled={saving}
        onblur={onBlur("WATCH_MAX_PASSES")}
      />
    </label>
    <label class="st-field">
      <span class="st-field-label">Min confidence</span>
      <input
        class="st-control narrow"
        value={settingsForm.MIN_GOAL_CONFIDENCE}
        placeholder="0.65"
        disabled={saving}
        onblur={onBlur("MIN_GOAL_CONFIDENCE")}
      />
    </label>
  </div>
</section>

<button
  type="button"
  class="st-advanced"
  onclick={() => (showAdvanced = !showAdvanced)}
  aria-expanded={showAdvanced}
>
  <span>{showAdvanced ? "Hide advanced" : "Show advanced"}</span>
  <span>{showAdvanced ? "▴" : "▾"}</span>
</button>

{#if showAdvanced}
  <section class="st-card muted">
    <div class="st-field-grid">
      <label class="st-field">
        <span class="st-field-label">Max tokens</span>
        <input
          class="st-control"
          type="number"
          min="256"
          max="32768"
          value={settingsForm.LLM_MAX_TOKENS}
          placeholder={settingsForm.GROQ_MAX_TOKENS || "4096"}
          disabled={saving}
          onblur={onBlur("LLM_MAX_TOKENS")}
        />
      </label>
      <label class="st-field">
        <span class="st-field-label">Max report revisions</span>
        <input
          class="st-control"
          value={settingsForm.MAX_REVISIONS}
          disabled={saving}
          onblur={onBlur("MAX_REVISIONS")}
        />
      </label>
      <label class="st-field">
        <span class="st-field-label">Results per search</span>
        <input
          class="st-control"
          value={settingsForm.RETRIEVAL_TOP_K}
          disabled={saving}
          onblur={onBlur("RETRIEVAL_TOP_K")}
        />
      </label>
    </div>
  </section>
{/if}
