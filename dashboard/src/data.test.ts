import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { PAGE_FILES, parsePage, toRecords, type RawPage } from "./data";

describe("toRecords", () => {
  it("zips columns and rows", () => {
    const rows = toRecords({ columns: ["a", "b"], types: ["int", "str"], rows: [[1, "x"], [2, null]] });
    expect(rows).toEqual([{ a: 1, b: "x" }, { a: 2, b: null }]);
  });
  it("rejects ragged rows", () => {
    expect(() => toRecords({ columns: ["a", "b"], types: ["int", "int"], rows: [[1]] })).toThrow();
  });
});

describe("committed page data", () => {
  for (const page of PAGE_FILES) {
    it(`${page}.json parses and matches its declared sources`, () => {
      const url = new URL(`../../exports/dashboard/${page}.json`, import.meta.url);
      const raw = JSON.parse(readFileSync(url, "utf-8")) as RawPage;
      const data = parsePage(raw);
      expect(data.page).toBe(page);
      for (const [name, rows] of Object.entries(data.tables)) {
        expect(rows.length).toBe(raw.sources[name].rows_kept);
      }
    });
  }
});
