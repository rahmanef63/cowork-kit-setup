"use client";
// Local CRUD dashboard over the shared on-disk datastore (.data/ + output/).
// It talks only to this app's own /api routes (which use Node fs under the hood) —
// no database, no API keys. The same records and documents are what the CLI writes
// and what Claude reads/writes through the MCP server.

import { useCallback, useEffect, useState } from "react";

type Row = Record<string, unknown>;

const META = ["created_at", "updated_at"];

function cell(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/** Union of all keys across records, ordered id -> fields -> created_at/updated_at. */
function columnsOf(rows: Row[]): string[] {
  const keys = new Set<string>();
  for (const r of rows) for (const k of Object.keys(r)) keys.add(k);
  const all = [...keys];
  const head = all.includes("id") ? ["id"] : [];
  const middle = all.filter((k) => k !== "id" && !META.includes(k));
  const tail = META.filter((k) => all.includes(k));
  return [...head, ...middle, ...tail];
}

async function errorText(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return (
      (j && typeof j.error === "string" && j.error) ||
      `Request failed (${res.status}).`
    );
  } catch {
    return `Request failed (${res.status}).`;
  }
}

export default function Page() {
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState("");
  const [newTable, setNewTable] = useState("");

  const [records, setRecords] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);

  const [createDraft, setCreateDraft] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  const [documents, setDocuments] = useState<string[]>([]);
  const [docName, setDocName] = useState<string | null>(null);
  const [docContent, setDocContent] = useState("");

  const loadTables = useCallback(async () => {
    try {
      const res = await fetch("/api/tables");
      if (!res.ok) return;
      const j = await res.json();
      setTables(Array.isArray(j.tables) ? j.tables : []);
    } catch {
      /* ignore — leave the current list in place */
    }
  }, []);

  const loadRecords = useCallback(async (table: string, q: string) => {
    if (!table) {
      setRecords([]);
      return;
    }
    setRecordsLoading(true);
    setRecordsError(null);
    try {
      const url = `/api/records/${encodeURIComponent(table)}${
        q ? `?q=${encodeURIComponent(q)}` : ""
      }`;
      const res = await fetch(url);
      if (!res.ok) {
        setRecordsError(await errorText(res));
        setRecords([]);
        return;
      }
      const j = await res.json();
      setRecords(Array.isArray(j.records) ? j.records : []);
    } catch (e) {
      setRecordsError(e instanceof Error ? e.message : String(e));
      setRecords([]);
    } finally {
      setRecordsLoading(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      const res = await fetch("/api/documents");
      if (!res.ok) return;
      const j = await res.json();
      setDocuments(Array.isArray(j.documents) ? j.documents : []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadTables();
    loadDocuments();
  }, [loadTables, loadDocuments]);

  // Reload records when the table changes or the search box settles (debounced).
  useEffect(() => {
    const t = setTimeout(() => loadRecords(selectedTable, query), 200);
    return () => clearTimeout(t);
  }, [selectedTable, query, loadRecords]);

  function openTable(name: string) {
    setSelectedTable(name);
    setEditingId(null);
    setCreateError(null);
    setRecordsError(null);
  }

  async function handleCreate() {
    setCreateError(null);
    if (!selectedTable.trim()) {
      setCreateError("Pick or name a table first.");
      return;
    }
    let data: unknown;
    try {
      data = JSON.parse(createDraft.trim() || "{}");
    } catch {
      setCreateError('Body must be valid JSON, e.g. {"name": "Acme"}.');
      return;
    }
    if (typeof data !== "object" || data === null || Array.isArray(data)) {
      setCreateError("Body must be a JSON object of fields.");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch(
        `/api/records/${encodeURIComponent(selectedTable)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      );
      if (!res.ok) {
        setCreateError(await errorText(res));
        return;
      }
      setCreateDraft("");
      await Promise.all([loadRecords(selectedTable, query), loadTables()]);
    } finally {
      setCreating(false);
    }
  }

  function startEdit(r: Row) {
    const rest: Row = {};
    for (const [k, v] of Object.entries(r)) {
      if (k === "id" || META.includes(k)) continue;
      rest[k] = v;
    }
    setEditingId(String(r.id));
    setEditDraft(JSON.stringify(rest, null, 2));
    setEditError(null);
  }

  async function handleSaveEdit(id: string) {
    setEditError(null);
    let data: unknown;
    try {
      data = JSON.parse(editDraft.trim() || "{}");
    } catch {
      setEditError("Body must be valid JSON.");
      return;
    }
    if (typeof data !== "object" || data === null || Array.isArray(data)) {
      setEditError("Body must be a JSON object of fields.");
      return;
    }
    const res = await fetch(
      `/api/records/${encodeURIComponent(selectedTable)}/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      },
    );
    if (!res.ok) {
      setEditError(await errorText(res));
      return;
    }
    setEditingId(null);
    setEditDraft("");
    loadRecords(selectedTable, query);
  }

  async function handleDelete(id: string) {
    if (!window.confirm(`Delete record ${id}? This cannot be undone.`)) return;
    const res = await fetch(
      `/api/records/${encodeURIComponent(selectedTable)}/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    );
    if (!res.ok) {
      setRecordsError(await errorText(res));
      return;
    }
    await Promise.all([loadRecords(selectedTable, query), loadTables()]);
  }

  async function openDoc(name: string) {
    setDocName(name);
    setDocContent("Loading…");
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(name)}`);
      if (!res.ok) {
        setDocContent(await errorText(res));
        return;
      }
      setDocContent(await res.text());
    } catch (e) {
      setDocContent(e instanceof Error ? e.message : String(e));
    }
  }

  const columns = columnsOf(records);

  return (
    <main className="page">
      <header className="page-header">
        <h1>Automation Data</h1>
        <p>
          Local CRUD over <code>.data/*.jsonl</code> and <code>output/</code> —
          the same files the CLI writes and Claude edits through the MCP server.
          No database, no API keys.
        </p>
      </header>

      <div className="grid">
        <div className="stack">
          <section className="card">
            <h2>Records</h2>

            <div className="row wrap">
              <select
                value={tables.includes(selectedTable) ? selectedTable : ""}
                onChange={(e) => openTable(e.target.value)}
              >
                <option value="">— pick a table —</option>
                {tables.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                className="grow"
                placeholder="or new table name…"
                value={newTable}
                onChange={(e) => setNewTable(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newTable.trim()) {
                    openTable(newTable.trim());
                    setNewTable("");
                  }
                }}
              />
              <button
                className="secondary"
                onClick={() => {
                  if (newTable.trim()) {
                    openTable(newTable.trim());
                    setNewTable("");
                  }
                }}
                disabled={!newTable.trim()}
              >
                Open
              </button>
            </div>

            {selectedTable && (
              <>
                <div className="row" style={{ marginTop: 12 }}>
                  <input
                    className="grow"
                    placeholder={`Search ${selectedTable}…`}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <button
                    className="secondary"
                    onClick={() => loadRecords(selectedTable, query)}
                  >
                    Refresh
                  </button>
                </div>

                <details className="create" open>
                  <summary>
                    New record in <code>{selectedTable}</code>
                  </summary>
                  <textarea
                    value={createDraft}
                    placeholder={'{\n  "name": "Acme Corp",\n  "stage": "lead"\n}'}
                    onChange={(e) => setCreateDraft(e.target.value)}
                  />
                  <div className="row">
                    <button onClick={handleCreate} disabled={creating}>
                      {creating ? "Creating…" : "Create record"}
                    </button>
                    <span className="hint">
                      id, created_at and updated_at are added automatically.
                    </span>
                  </div>
                  {createError && <p className="error">{createError}</p>}
                </details>
              </>
            )}

            {!selectedTable && (
              <div className="empty" style={{ marginTop: 12 }}>
                Pick a table above (or type a new name) to view and edit its
                records.
              </div>
            )}

            {selectedTable && (
              <div className="table-wrap">
                {recordsLoading && <div className="empty">Loading…</div>}
                {recordsError && <p className="error">{recordsError}</p>}
                {!recordsLoading && !recordsError && records.length === 0 && (
                  <div className="empty">
                    No records in <code>{selectedTable}</code> yet.
                  </div>
                )}
                {!recordsLoading && records.length > 0 && (
                  <table className="data">
                    <thead>
                      <tr>
                        {columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                        <th className="actions-col">actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((r) => {
                        const id = String(r.id ?? "");
                        if (editingId === id) {
                          return (
                            <tr key={id} className="editing">
                              <td colSpan={columns.length + 1}>
                                <div className="edit-box">
                                  <div className="label">
                                    editing <code>{id}</code>
                                  </div>
                                  <textarea
                                    value={editDraft}
                                    onChange={(e) => setEditDraft(e.target.value)}
                                  />
                                  <div className="row">
                                    <button onClick={() => handleSaveEdit(id)}>
                                      Save
                                    </button>
                                    <button
                                      className="secondary"
                                      onClick={() => {
                                        setEditingId(null);
                                        setEditError(null);
                                      }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                  {editError && (
                                    <p className="error">{editError}</p>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        }
                        return (
                          <tr key={id}>
                            {columns.map((c) => (
                              <td key={c} title={cell(r[c])}>
                                {cell(r[c])}
                              </td>
                            ))}
                            <td className="actions-col">
                              <button
                                className="mini"
                                onClick={() => startEdit(r)}
                              >
                                Edit
                              </button>
                              <button
                                className="mini danger"
                                onClick={() => handleDelete(id)}
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
                {records.length > 0 && (
                  <div className="hint" style={{ marginTop: 8 }}>
                    {records.length} record(s)
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        <div className="stack">
          <section className="card">
            <h2>Documents</h2>
            <div className="row" style={{ marginBottom: 10 }}>
              <button className="secondary" onClick={loadDocuments}>
                Refresh
              </button>
              <span className="hint">
                files in <code>output/</code>
              </span>
            </div>
            {documents.length === 0 && (
              <div className="empty">No documents yet.</div>
            )}
            <ul className="list">
              {documents.map((d) => (
                <li key={d}>
                  <button className="linklike" onClick={() => openDoc(d)}>
                    {d}
                  </button>
                </li>
              ))}
            </ul>

            {docName && (
              <div className="doc-view">
                <div className="row between">
                  <div className="label">
                    <code>{docName}</code>
                  </div>
                  <button
                    className="mini secondary"
                    onClick={() => {
                      setDocName(null);
                      setDocContent("");
                    }}
                  >
                    Close
                  </button>
                </div>
                <pre>{docContent}</pre>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
