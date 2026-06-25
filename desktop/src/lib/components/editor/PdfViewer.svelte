<script lang="ts">
  import { onMount } from "svelte";
  import * as pdfjs from "pdfjs-dist";
  import { readPdfBytes } from "$lib/vault/pdf";
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
  let pdfDoc: pdfjs.PDFDocumentProxy | null = null;

  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url,
  ).toString();

  async function renderPage() {
    if (!pdfDoc || !canvasEl) return;
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: zoom });
    const ctx = canvasEl.getContext("2d");
    if (!ctx) return;
    canvasEl.width = viewport.width;
    canvasEl.height = viewport.height;
    await page.render({ canvasContext: ctx, viewport, canvas: canvasEl }).promise;
  }

  async function loadPdf() {
    loading = true;
    error = "";
    workspace.setActiveNote(path);
    try {
      const bytes = await readPdfBytes(path);
      pdfDoc = await pdfjs.getDocument({ data: bytes }).promise;
      pageCount = pdfDoc.numPages;
      if (workspace.pdfJumpPage && workspace.pdfJumpPage <= pageCount) {
        pageNum = workspace.pdfJumpPage;
        workspace.pdfJumpPage = null;
      } else {
        pageNum = 1;
      }
      await renderPage();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load PDF";
    } finally {
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
    void path;
    void loadPdf();
  });
</script>

<section class="panel">
  <div class="toolbar">
    <div>
      <h2>{path.split("/").pop()}</h2>
      <p class="hint path-hint">{path}</p>
    </div>
    <div class="controls">
      <button onclick={prevPage} disabled={pageNum <= 1}>Prev</button>
      <span class="page-label">{pageNum} / {pageCount || "—"}</span>
      <button onclick={nextPage} disabled={pageNum >= pageCount}>Next</button>
      <button onclick={zoomOut}>−</button>
      <button onclick={zoomIn}>+</button>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading PDF…</div>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <div class="canvas-wrap">
      <canvas bind:this={canvasEl}></canvas>
    </div>
  {/if}
</section>

<style>
  .panel h2 {
    font-size: 1.2rem;
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
    font-size: 0.75rem;
    padding: 0.35rem 0.55rem;
  }

  .page-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    min-width: 4rem;
    text-align: center;
  }

  .path-hint {
    font-size: 0.75rem;
    word-break: break-all;
    color: var(--text-muted);
  }

  .canvas-wrap {
    overflow: auto;
    max-height: 75vh;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem;
  }

  canvas {
    display: block;
    margin: 0 auto;
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
  }

  .error {
    color: var(--error);
  }
</style>