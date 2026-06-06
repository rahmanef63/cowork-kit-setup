// web/lib/store.ts
//
// Server-only filesystem datastore. This reads and writes the SAME on-disk format
// as the Python CLI (local/automation/tools.py) and the MCP server (mcp/store.py),
// so the website, the CLI, and Claude (via the MCP) all share one source of truth:
//
//   <workspace>/.data/<table>.jsonl   one JSON object per line, each with an "id"
//   <workspace>/output/<file>         documents / deliverables
//
// Workspace = $AUTOMATION_WORKSPACE if set, otherwise the project root — which is
// the PARENT of web/, because `next dev` runs from web/ (so process.cwd() === web/).
//
// IMPORTANT: this module imports node:fs and must never be imported from a client
// component. Only the route handlers under app/api/** use it.

import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

export type RecordRow = Record<string, unknown>;

/** The project root that the CLI, the MCP server, and this website all share. */
export function workspace(): string {
  const env = process.env.AUTOMATION_WORKSPACE;
  return env ? path.resolve(env) : path.resolve(process.cwd(), "..");
}

function dataDir(): string {
  const d = path.join(workspace(), ".data");
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function outputDir(): string {
  const d = path.join(workspace(), "output");
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function nowIso(): string {
  return new Date().toISOString();
}

/** 12-char hex id, matching Python's uuid.uuid4().hex[:12]. */
function newId(): string {
  return randomUUID().replace(/-/g, "").slice(0, 12);
}

/** Keep letters/digits plus - and _, then trim leading/trailing - and _.
 *  Mirrors Python's _safe_table(). */
function safeTable(table: string): string {
  return String(table)
    .replace(/[^\p{L}\p{N}_-]/gu, "")
    .replace(/^[-_]+/, "")
    .replace(/[-_]+$/, "");
}

/** Basename only — strips any directory components. Mirrors Python's Path(name).name. */
function safeName(name: string): string {
  return path.basename(String(name));
}

function tablePath(safe: string): string {
  return path.join(dataDir(), `${safe}.jsonl`);
}

function readTable(safe: string): RecordRow[] {
  const p = tablePath(safe);
  if (!fs.existsSync(p)) return [];
  const rows: RecordRow[] = [];
  for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      rows.push(JSON.parse(trimmed) as RecordRow);
    } catch {
      // Skip malformed lines, same as the Python side ignores JSONDecodeError.
    }
  }
  return rows;
}

function writeTable(safe: string, rows: RecordRow[]): void {
  const body = rows.map((r) => JSON.stringify(r) + "\n").join("");
  fs.writeFileSync(tablePath(safe), body, "utf8");
}

// --------------------------------------------------------------------------- //
// Records CRUD
// --------------------------------------------------------------------------- //

/** Sorted names of every <table>.jsonl in .data/. */
export function listTables(): string[] {
  return fs
    .readdirSync(dataDir())
    .filter((f) => f.endsWith(".jsonl"))
    .map((f) => f.slice(0, -".jsonl".length))
    .sort();
}

/** All records in a table, optionally filtered by a case-insensitive substring
 *  match over any field value. */
export function listRecords(table: string, query = ""): RecordRow[] {
  const rows = readTable(safeTable(table));
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((r) =>
    Object.values(r).some((v) => String(v).toLowerCase().includes(needle)),
  );
}

/** One record by id, or null. */
export function getRecord(table: string, id: string): RecordRow | null {
  for (const r of readTable(safeTable(table))) {
    if (r.id === id) return r;
  }
  return null;
}

/** Create a record. Adds id, created_at and updated_at; returns the new record. */
export function createRecord(table: string, data: RecordRow): RecordRow {
  const safe = safeTable(table);
  if (!safe) throw new Error("invalid table name");
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("data must be an object");
  }
  const rows = readTable(safe);
  const now = nowIso();
  const rec: RecordRow = { id: newId(), ...data, created_at: now, updated_at: now };
  rows.push(rec);
  writeTable(safe, rows);
  return rec;
}

/** Merge fields into a record by id (id preserved, updated_at refreshed).
 *  Returns the updated record, or null if no record matched. */
export function updateRecord(
  table: string,
  id: string,
  data: RecordRow,
): RecordRow | null {
  const safe = safeTable(table);
  const rows = readTable(safe);
  let out: RecordRow | null = null;
  for (const r of rows) {
    if (r.id === id) {
      Object.assign(r, data);
      r.id = id;
      r.updated_at = nowIso();
      out = r;
      break;
    }
  }
  if (out !== null) writeTable(safe, rows);
  return out;
}

/** Delete a record by id. Returns true if a record was removed. */
export function deleteRecord(table: string, id: string): boolean {
  const safe = safeTable(table);
  const rows = readTable(safe);
  const kept = rows.filter((r) => r.id !== id);
  if (kept.length === rows.length) return false;
  writeTable(safe, kept);
  return true;
}

// --------------------------------------------------------------------------- //
// Documents
// --------------------------------------------------------------------------- //

/** Sorted names of the files in output/. */
export function listDocuments(): string[] {
  return fs
    .readdirSync(outputDir(), { withFileTypes: true })
    .filter((e) => e.isFile())
    .map((e) => e.name)
    .sort();
}

/** Read a document's text, or null if it does not exist. */
export function readDoc(name: string): string | null {
  const p = path.join(outputDir(), safeName(name));
  if (!fs.existsSync(p) || !fs.statSync(p).isFile()) return null;
  return fs.readFileSync(p, "utf8");
}

/** Create or overwrite a document. Returns its workspace-relative path. */
export function writeDoc(name: string, content: string): string {
  const safe = safeName(name);
  if (!safe) throw new Error("invalid file name");
  fs.writeFileSync(path.join(outputDir(), safe), String(content), "utf8");
  return `output/${safe}`;
}
