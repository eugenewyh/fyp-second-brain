import { describe, expect, it } from "vitest";
import { ideaBodyFromMarkdown } from "../vault/project-edit";
import { isRememberableNotePath } from "../vault/rememberable";
import { channelLooksEmpty } from "./channel-empty";

describe("channelLooksEmpty", () => {
  it("is empty with only a stub readme and blank idea", () => {
    expect(
      channelLooksEmpty({
        idea: "",
        claimCount: 0,
        notePaths: ["/vault/Inbox/README.md"],
      }),
    ).toBe(true);
  });

  it("is ready when IDEA has a body", () => {
    expect(
      channelLooksEmpty({
        idea: "Track DLM vs JSON.",
        claimCount: 0,
        notePaths: [],
      }),
    ).toBe(false);
  });

  it("is ready when claims exist", () => {
    expect(
      channelLooksEmpty({
        idea: "",
        claimCount: 1,
        notePaths: [],
      }),
    ).toBe(false);
  });

  it("is ready when a real note exists", () => {
    expect(
      channelLooksEmpty({
        idea: "",
        claimCount: 0,
        notePaths: ["/vault/FYP/notes.md"],
      }),
    ).toBe(false);
  });
});

describe("rememberable vs idea header", () => {
  it("skips IDEA.md and README.md", () => {
    expect(isRememberableNotePath("/vault/FYP/IDEA.md")).toBe(false);
    expect(isRememberableNotePath("/vault/FYP/README.md")).toBe(false);
    expect(isRememberableNotePath("/vault/FYP/notes.md")).toBe(true);
  });

  it("treats a header-only IDEA as empty body", () => {
    expect(ideaBodyFromMarkdown("# Idea\n\n")).toBe("");
  });
});
