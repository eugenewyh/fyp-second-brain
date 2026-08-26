import { describe, expect, it } from "vitest";
import { sourceLookupName } from "./source-origin";
import { resolveSourcePath } from "./source-path";

const vaultFiles = [
  {
    path: "/vault/Second-Brain-Lab/research/2026-08-06-091214-based-on-my-library-and-prior-research-g3-ablati.md",
    name: "2026-08-06-091214-based-on-my-library-and-prior-research-g3-ablati.md",
  },
];

describe("sourceLookupName", () => {
  it("strips Personal em-dash prefix", () => {
    expect(
      sourceLookupName(
        "Personal — 2026-08-06-091214-based-on-my-library-and-prior-research-g3-ablati.md",
      ),
    ).toBe("2026-08-06-091214-based-on-my-library-and-prior-research-g3-ablati.md");
  });
});

describe("resolveSourcePath", () => {
  it("maps bibliography labels to the real vault file", () => {
    expect(
      resolveSourcePath(
        "Personal — 2026-08-06-091214-based-on-my-library-and-prior-research-g3-ablati.md",
        "/vault",
        vaultFiles,
      ),
    ).toBe(vaultFiles[0].path);
  });

  it("does not invent vaultRoot/label when the file is missing", () => {
    expect(
      resolveSourcePath("Personal — missing.md", "/vault", vaultFiles),
    ).toBeNull();
  });
});
