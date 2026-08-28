import { describe, expect, it } from "vitest";
import {
  COACH_STEPS,
  COMPOSER_SKILLS,
  forcedJobLabel,
  skillForJob,
  skillPlaceholder,
} from "./composer-skills";

describe("COMPOSER_SKILLS", () => {
  it("covers Auto plus Teach, Ask, Research", () => {
    expect(COMPOSER_SKILLS.map((s) => s.id)).toEqual([
      "auto",
      "teach",
      "ask",
      "research",
    ]);
  });
});

describe("skill helpers", () => {
  it("maps forced jobs to labels and placeholders", () => {
    expect(forcedJobLabel("file")).toBe("Teach");
    expect(forcedJobLabel("watch")).toBe("Research");
    expect(forcedJobLabel(null)).toBe("Auto");
    expect(skillPlaceholder("file")).toMatch(/remember/i);
    expect(skillForJob("research").id).toBe("research");
  });
});

describe("COACH_STEPS", () => {
  it("teaches topic → Teach → Ask/Research", () => {
    expect(COACH_STEPS).toHaveLength(3);
    expect(COACH_STEPS[1]?.title.toLowerCase()).toContain("teach");
    expect(COACH_STEPS[2]?.body.toLowerCase()).toContain("scheduled research");
  });
});
