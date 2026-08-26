<script lang="ts">
  import { tick } from "svelte";
  import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
  import { readPdfBytes, resolveBarePdf } from "$lib/vault/pdf";
  import { workspace } from "$lib/stores/workspace.svelte";

  interface Props {
    path: string;
  }

  let { path }: Props = $props();

  let canvasEl: HTMLCanvasElement | undefined = $state();
  let pageNum = $state(1);
  let pageCount = $state(0);
  let zoom = $state(1.2);
  let loading = $state(true);
  let error = $state("");
  let pdfDoc: any = null;
  let loadGeneration = 0;

  // Force main-thread parsing (no worker script headaches in Tauri webview)
  (pdfjsLib as any).GlobalWorkerOptions.workerSrc = "";

  async function renderPage() {
    if (!pdfDoc || !canvasEl) return;
    try {
      const page = await pdfDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: zoom });
      const ctx = canvasEl.getContext("2d", { alpha: false });
      if (!ctx) return;
      canvasEl.width = Math.floor(viewport.width);
      canvasEl.height = Math.floor(viewport.height);
      await page.render({ canvasContext: ctx, viewport, canvas: canvasEl }).promise;
    } catch (e) {
      console.error("[PDF] render error", e);
    }
  }

  async function loadPdf(signal: { cancelled: boolean }) {
    const gen = ++loadGeneration;
    loading = true;
    error = "";
    pdfDoc = null;
    pageCount = 0;

    let bytes: Uint8Array | null = null;
    const tried = await resolveBarePdf(path);
    try {
      bytes = await readPdfBytes(tried);
      if (signal.cancelled || gen !== loadGeneration) return;
      if (!bytes || bytes.length < 4) {
        throw new Error(`Read 0 bytes for "${tried}" (file not found or empty on disk)`);
      }

      const head = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
      if (head !== "%PDF") {
        throw new Error(`Not a valid PDF for "${tried}" (magic="${head}", len=${bytes.length})`);
      }

      const data = new Uint8Array(bytes);

      // Main-thread parse (no worker)
      const task = (pdfjsLib as any).getDocument({
        data,
        disableWorker: true,
        useSystemFonts: true,
      });
      pdfDoc = await task.promise;

      if (signal.cancelled || gen !== loadGeneration) return;

      pageCount = pdfDoc.numPages || 0;
      if (pageCount === 0) {
        throw new Error(`PDF parsed but reported 0 pages (len=${bytes.length})`);
      }

      if (workspace.pdfJumpPage && workspace.pdfJumpPage <= pageCount) {
        pageNum = workspace.pdfJumpPage;
        workspace.pdfJumpPage = null;
      } else {
        pageNum = 1;
      }

      loading = false;
      await tick();
      await renderPage();
    } catch (e: any) {
      if (signal.cancelled || gen !== loadGeneration) return;
      console.error("[PDF] load failed for", path, e);
      const msg =
        (e && (e.message || e.toString?.())) ||
        (typeof e === "string" ? e : JSON.stringify(e)) ||
        "Failed to load PDF";
      error = msg;
      loading = false;
    }
  }

  function prevPage() {
    if (pageNum > 1) {
      pageNum -= 1;
      void renderPage();
    }
  }

  function nextPage() {
    if (pageNum < pageCount) {
      pageNum += 1;
      void renderPage();
    }
  }

  function zoomIn() {
    zoom = Math.min(zoom + 0.2, 3);
    void renderPage();
  }

  function zoomOut() {
    zoom = Math.max(zoom - 0.2, 0.6);
    void renderPage();
  }

  $effect(() => {
    const signal = { cancelled: false };
    void path;
    void loadPdf(signal);
    return () => {
      signal.cancelled = true;
    };
  });

  // If a bare filename like "Lec03.pdf" was passed (from recent/sources),
  // upgrade it to a real path so the file can be opened again later.
  $effect(() => {
    const p = path;
    if (!p || p.includes("/") || p.includes("\\")) return;
    if (!p.toLowerCase().endsWith(".pdf")) return;
    (async () => {
      try {
        const resolved = await resolveBarePdf(p);
        if (resolved !== p) {
          const { tabs } = await import("$lib/stores/tabs.svelte");
          tabs.openNoteTab(resolved, resolved.split("/").pop() ?? resolved);
          workspace.setActiveNote(resolved);
        }
      } catch {}
    })();
  });

  $effect(() => {
    void pageNum;
    void zoom;
    if (!loading && pdfDoc) void renderPage();
  });
</script>

<section class="panel">
  <div class="toolbar">
    <div>
      <h2>{path.split("/").pop()}</h2>
      <p class="hint path-hint">{path}</p>
    </div>
    <div class="controls">
      <button type="button" onclick={prevPage} disabled={pageNum <= 1 || loading}>Prev</button>
      <span class="page-label">{pageNum} / {pageCount || "—"}</span>
      <button type="button" onclick={nextPage} disabled={pageNum >= pageCount || loading}>Next</button>
      <button type="button" onclick={zoomOut} disabled={loading || !pageCount}>−</button>
      <button type="button" onclick={zoomIn} disabled={loading || !pageCount}>+</button>
    </div>
  </div>

  {#if error}
    <div class="error-box">
      <p class="error-title">Couldn't open this PDF</p>
      <p class="error-body">
        It may have been moved or removed. Try adding the document again from Library.
      </p>
      <button
        type="button"
        class="btn-secondary"
        onclick={() => workspace.openUtilityPanel("ingest")}
      >
        Add documents
      </button>
      <details class="tech">
        <summary>Technical details</summary>
        <p class="detail">{path}</p>
        <p class="detail">{error}</p>
      </details>
    </div>
  {/if}

  <div class="canvas-wrap">
    {#if loading}
      <div class="loading-overlay">Loading PDF…</div>
    {/if}
    <canvas bind:this={canvasEl}></canvas>
  </div>
</section>

<style>
  .panel h2 {
    font-size: var(--text-xl);
    margin-bottom: 0.2rem;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .controls button {
    font-size: var(--text-sm);
    padding: 0.35rem 0.55rem;
  }

  .page-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    min-width: 4rem;
    text-align: center;
  }

  .path-hint {
    font-size: var(--text-sm);
    word-break: break-all;
    color: var(--text-muted);
  }

  .canvas-wrap {
    position: relative;
    overflow: auto;
    max-height: 75vh;
    min-height: 200px;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem;
  }

  canvas {
    display: block;
    margin: 0 auto;
    max-width: 100%;
  }

  .loading-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--bg-elevated) 85%, transparent);
    color: var(--warning);
    z-index: 1;
    pointer-events: none;
  }

  .error-box {
    margin: 1.5rem;
    padding: 1.25rem;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    max-width: 28rem;
  }

  .error-title {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text);
    margin-bottom: 0.35rem;
  }

  .error-body {
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.5;
    margin-bottom: 0.75rem;
  }

  .error-box .tech {
    margin-top: 0.75rem;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .error-box .detail {
    font-family: var(--font-mono);
    word-break: break-all;
    margin-top: 0.25rem;
  }
</style>
