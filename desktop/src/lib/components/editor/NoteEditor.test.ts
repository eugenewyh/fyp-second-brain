import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount } from "svelte";
import NoteEditor from "./NoteEditor.svelte";
import { tabs } from "$lib/stores/tabs.svelte";
import { workspace } from "$lib/stores/workspace.svelte";

const vaultTree = [
  { name: "other-note.md", path: "/vault/other-note.md", type: "file" as const },
];

vi.mock("$lib/vault/load", () => ({
  readNote: vi.fn(async () => "---\ntitle: Test\n---\nSee [[other-note|Other]] here.\n"),
  writeNote: vi.fn(async () => undefined),
  loadVaultTree: vi.fn(async () => vaultTree),
  getVaultRoot: vi.fn(async () => "/vault"),
}));

describe("NoteEditor.svelte (mounted)", () => {
  let target: HTMLDivElement;
  let instance: ReturnType<typeof mount> | null = null;

  beforeEach(() => {
    target = document.body.appendChild(document.createElement("div"));
    workspace.vaultRefreshNonce = 0;
    workspace.vaultRoot = "/vault";
  });

  afterEach(() => {
    if (instance) unmount(instance);
    instance = null;
    target.remove();
    vi.clearAllMocks();
  });

  it("mounts TipTap surface and save calls writeNote with serialized markdown", async () => {
    const { writeNote } = await import("$lib/vault/load");
    const refreshSpy = vi.spyOn(workspace, "requestVaultRefresh");
    const nonceBefore = workspace.vaultRefreshNonce;

    instance = mount(NoteEditor, { target, props: { path: "/vault/test.md" } });

    await vi.waitUntil(() => target.querySelector(".tiptap-surface"), { timeout: 5000 });

    const saveBtn = [...target.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Save"),
    ) as HTMLButtonElement;
    expect(saveBtn).toBeTruthy();
    saveBtn.click();

    await vi.waitUntil(() => vi.mocked(writeNote).mock.calls.length > 0, { timeout: 3000 });
    await vi.waitUntil(() => refreshSpy.mock.calls.length > 0, { timeout: 3000 });

    const [, content] = vi.mocked(writeNote).mock.calls[0];
    expect(content).toContain("[[other-note|Other]]");
    expect(refreshSpy).toHaveBeenCalled();
    expect(workspace.vaultRefreshNonce).toBeGreaterThan(nonceBefore);
  });

  it("wikilink click opens resolved note via tabs + workspace", async () => {
    const openSpy = vi.spyOn(tabs, "openNoteTab");
    const setActiveSpy = vi.spyOn(workspace, "setActiveNote");

    instance = mount(NoteEditor, { target, props: { path: "/vault/test.md" } });

    await vi.waitUntil(() => target.querySelector("a[data-wikilink]"), { timeout: 5000 });

    const link = target.querySelector("a[data-wikilink]") as HTMLAnchorElement;
    link.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(openSpy).toHaveBeenCalledWith("/vault/other-note.md");
    expect(setActiveSpy).toHaveBeenCalledWith("/vault/other-note.md");
  });
});