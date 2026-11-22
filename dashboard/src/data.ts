// Loads the per-page JSON written by scripts/build_dashboard_data.py from committed exports.

export type Cell = string | number | boolean | null;
export type Row = Record<string, Cell>;

export interface RawTable {
  columns: string[];
  types: string[];
  rows: Cell[][];
}

export interface Source {
  path: string;
  sha256: string;
  rows_kept: number;
}

export interface RawPage {
  page: string;
  sources: Record<string, Source>;
  tables: Record<string, RawTable>;
}

export interface PageData {
  page: string;
  sources: Record<string, Source>;
  tables: Record<string, Row[]>;
}

export const PAGE_FILES = ["headline", "decomposition", "segments", "budget"] as const;
export type PageFile = (typeof PAGE_FILES)[number];

export function toRecords(table: RawTable): Row[] {
  return table.rows.map((row) => {
    if (row.length !== table.columns.length) {
      throw new Error(`row has ${row.length} cells, expected ${table.columns.length}`);
    }
    const out: Row = {};
    table.columns.forEach((c, i) => (out[c] = row[i]));
    return out;
  });
}

export function parsePage(raw: RawPage): PageData {
  const tables: Record<string, Row[]> = {};
  for (const [name, t] of Object.entries(raw.tables)) tables[name] = toRecords(t);
  return { page: raw.page, sources: raw.sources, tables };
}

const cache = new Map<PageFile, Promise<PageData>>();

export function loadPage(page: PageFile): Promise<PageData> {
  let p = cache.get(page);
  if (!p) {
    p = fetch(`${import.meta.env.BASE_URL}dashboard/${page}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`${page}.json: HTTP ${r.status}`);
        return r.json() as Promise<RawPage>;
      })
      .then(parsePage);
    cache.set(page, p);
  }
  return p;
}

export function num(row: Row, col: string): number {
  const v = row[col];
  if (typeof v !== "number") throw new Error(`${col} is not a number`);
  return v;
}
