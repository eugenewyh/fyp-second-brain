import { describe, expect, it } from "vitest";
import { isRememberableNotePath } from "./rememberable";
import { shouldSkipWatcherIngest } from "./watcher-skip";

describe("shouldSkipWatcherIngest", () => {
  it("skips Watch/Teach write paths so ingest cannot recurse", () => {
    expect(shouldSkipWatcherIngest("/vault/Inbox/instruction.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/briefs/2026-08-17.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/memory/claims/c.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/research/report.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/watches/morning/instruction.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/watches/morning/briefs/2026-08-18.md")).toBe(true);
    expect(shouldSkipWatcherIngest("/vault/Inbox/notes.md")).toBe(false);
  });
});

describe("isRememberableNotePath", () => {
  it("keeps imported reading notes and skips stubs plus traces", () => {
    expect(isRememberableNotePath("/vault/dlm/dlm/01-my-stance-dlm.md")).toBe(true);
    expect(isRememberableNotePath("/vault/dlm/instruction.md")).toBe(false);
    expect(isRememberableNotePath("/vault/dlm/IDEA.md")).toBe(false);
    expect(isRememberableNotePath("/vault/dlm/README.md")).toBe(false);
    expect(isRememberableNotePath("/vault/dlm/research/report.md")).toBe(false);
  });
});
