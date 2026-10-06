import { describe, expect, it } from "vitest";
import { uniqueName, validateItemName } from "./names";

describe("validateItemName", () => {
  const siblings = [{ id: "1", name: "Photos" }, { id: "2", name: "a.txt" }];
  it("rejects blank and whitespace-only names", () => {
    expect(validateItemName("", siblings)).toMatch(/enter a name/);
    expect(validateItemName("   ", siblings)).toMatch(/enter a name/);
  });
  it("rejects duplicates case-insensitively but allows renaming to itself", () => {
    expect(validateItemName("photos", siblings)).toMatch(/already exists/);
    expect(validateItemName("Photos", siblings, "1")).toBeNull();
  });
  it("rejects slashes and dot names", () => {
    expect(validateItemName("a/b", siblings)).not.toBeNull();
    expect(validateItemName("..", siblings)).not.toBeNull();
  });
  it("accepts a normal new name", () => {
    expect(validateItemName("Docs", siblings)).toBeNull();
  });
});

describe("uniqueName", () => {
  it("adds a counter before the extension", () => {
    expect(uniqueName("a.txt", ["a.txt"])).toBe("a (1).txt");
    expect(uniqueName("a.txt", ["A.TXT", "a (1).txt"])).toBe("a (2).txt");
    expect(uniqueName("README", ["readme"])).toBe("README (1)");
    expect(uniqueName("new.txt", ["a.txt"])).toBe("new.txt");
  });
});
