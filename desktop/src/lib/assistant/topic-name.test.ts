import { describe, expect, it } from "vitest";
import { suggestTopicName } from "./topic-name";

describe("suggestTopicName", () => {
  it("pulls the subject out of a lookup", () => {
    expect(suggestTopicName("Find papers on JustGRPO")).toBe("JustGRPO");
  });

  it("uses FYP/thesis as the folder name", () => {
    expect(suggestTopicName("help with my FYP")).toBe("FYP");
  });

  it("falls back to Research", () => {
    expect(suggestTopicName("")).toBe("Research");
  });
});
