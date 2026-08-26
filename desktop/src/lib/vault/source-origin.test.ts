import { describe, expect, it } from "vitest";
import {
  classifySourceOrigin,
  originShort,
  sourceLookupName,
} from "./source-origin";

describe("classifySourceOrigin", () => {
  it("detects Notion URLs before generic web", () => {
    expect(classifySourceOrigin("https://www.notion.so/aaaaaaaa")).toBe("notion");
  });

  it("detects Notion bibliography prefix", () => {
    expect(
      classifySourceOrigin("Notion — Meeting notes (https://www.notion.so/aaaaaaaa)"),
    ).toBe("notion");
  });
});

describe("originShort", () => {
  it("labels notion", () => {
    expect(originShort("notion")).toBe("Notion");
  });
});

describe("sourceLookupName", () => {
  it("strips Notion em-dash prefix", () => {
    expect(
      sourceLookupName("Notion — Meeting notes (https://www.notion.so/aaaaaaaa)"),
    ).toBe("Meeting notes (https://www.notion.so/aaaaaaaa)");
  });
});
