import { describe, test, expect } from "vitest";
import { getScoreBand } from "./score.js";

describe("getScoreBand", () => {
  test("maps tier boundaries per the spec: ≥85 hot, 70–84 warm, <70 cool", () => {
    expect(getScoreBand(100)).toBe("hot");
    expect(getScoreBand(85)).toBe("hot");
    expect(getScoreBand(84)).toBe("warm");
    expect(getScoreBand(70)).toBe("warm");
    expect(getScoreBand(69)).toBe("cool");
    expect(getScoreBand(0)).toBe("cool");
  });
});
