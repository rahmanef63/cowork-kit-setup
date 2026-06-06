// Purpose: Convex data layer for the agent — internal read/write functions the
// tool dispatcher uses, run lifecycle helpers, and public queries for the UI.

import {
  internalMutation,
  internalQuery,
  mutation,
  query,
} from "./_generated/server";
import { v } from "convex/values";

// ---------------------------------------------------------------------------
// documents
// ---------------------------------------------------------------------------

/** Insert or replace a document by name (write_deliverable). */
export const writeDocument = internalMutation({
  args: { name: v.string(), content: v.string() },
  handler: async (ctx, { name, content }) => {
    const existing = await ctx.db
      .query("documents")
      .withIndex("by_name", (q) => q.eq("name", name))
      .order("desc")
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, { content, updatedAt: Date.now() });
      return name;
    }
    await ctx.db.insert("documents", { name, content, updatedAt: Date.now() });
    return name;
  },
});

/** Read the latest document for a name (read_document). */
export const getDocument = internalQuery({
  args: { name: v.string() },
  handler: async (ctx, { name }) => {
    return await ctx.db
      .query("documents")
      .withIndex("by_name", (q) => q.eq("name", name))
      .order("desc")
      .first();
  },
});

/** List document names, optionally filtered by a case-insensitive substring (list_workspace). */
export const listDocuments = internalQuery({
  args: { pattern: v.optional(v.string()) },
  handler: async (ctx, { pattern }) => {
    const docs = await ctx.db.query("documents").collect();
    const needle = pattern?.toLowerCase();
    const names: string[] = [];
    const seen = new Set<string>();
    for (const d of docs) {
      if (seen.has(d.name)) continue;
      if (needle && !d.name.toLowerCase().includes(needle)) continue;
      seen.add(d.name);
      names.push(d.name);
    }
    return names.sort();
  },
});

// ---------------------------------------------------------------------------
// records
// ---------------------------------------------------------------------------

/** Append a record to a logical table (save_record). */
export const addRecord = internalMutation({
  args: { table: v.string(), data: v.any() },
  handler: async (ctx, { table, data }) => {
    return await ctx.db.insert("records", {
      table,
      data,
      createdAt: Date.now(),
    });
  },
});

/** Substring-search records in a table by the JSON of their data (lookup_record). */
export const queryRecords = internalQuery({
  args: { table: v.string(), query: v.optional(v.string()) },
  handler: async (ctx, { table, query }) => {
    const rows = await ctx.db
      .query("records")
      .withIndex("by_table", (q) => q.eq("table", table))
      .collect();
    if (!query) return rows;
    const needle = query.toLowerCase();
    return rows.filter((r) =>
      JSON.stringify(r.data).toLowerCase().includes(needle),
    );
  },
});

// ---------------------------------------------------------------------------
// tasks
// ---------------------------------------------------------------------------

/** Create a follow-up task (create_task). */
export const addTask = internalMutation({
  args: {
    title: v.string(),
    due: v.optional(v.string()),
    notes: v.optional(v.string()),
  },
  handler: async (ctx, { title, due, notes }) => {
    return await ctx.db.insert("tasks", {
      title,
      due,
      notes,
      done: false,
      createdAt: Date.now(),
    });
  },
});

// ---------------------------------------------------------------------------
// runs (lifecycle + live transcript)
// ---------------------------------------------------------------------------

/** Create a new run row in the "running" state and return its id. */
export const createRun = internalMutation({
  args: { sessionId: v.string(), task: v.string() },
  handler: async (ctx, { sessionId, task }) => {
    const now = Date.now();
    return await ctx.db.insert("runs", {
      sessionId,
      task,
      status: "running",
      transcript: [],
      createdAt: now,
      updatedAt: now,
    });
  },
});

/** Append a complete transcript event (tool_call, tool_result, error, ...). */
export const appendRunEvent = internalMutation({
  args: { runId: v.id("runs"), event: v.any() },
  handler: async (ctx, { runId, event }) => {
    const run = await ctx.db.get(runId);
    if (!run) return;
    await ctx.db.patch(runId, {
      transcript: [...run.transcript, event],
      updatedAt: Date.now(),
    });
  },
});

/**
 * Append a text delta to the in-progress assistant message so the UI updates
 * live. If the last event is an assistant message, extend it; otherwise start
 * a new one (e.g. after a tool round).
 */
export const appendAssistantDelta = internalMutation({
  args: { runId: v.id("runs"), delta: v.string() },
  handler: async (ctx, { runId, delta }) => {
    const run = await ctx.db.get(runId);
    if (!run) return;
    const transcript = [...run.transcript];
    const last = transcript[transcript.length - 1];
    if (last && last.type === "assistant") {
      transcript[transcript.length - 1] = {
        ...last,
        text: (last.text ?? "") + delta,
      };
    } else {
      transcript.push({ type: "assistant", text: delta });
    }
    await ctx.db.patch(runId, { transcript, updatedAt: Date.now() });
  },
});

/** Mark a run done/error, optionally appending an error event. */
export const setRunStatus = internalMutation({
  args: {
    runId: v.id("runs"),
    status: v.union(
      v.literal("running"),
      v.literal("done"),
      v.literal("error"),
    ),
    error: v.optional(v.string()),
  },
  handler: async (ctx, { runId, status, error }) => {
    const run = await ctx.db.get(runId);
    if (!run) return;
    const transcript = error
      ? [...run.transcript, { type: "error", message: error }]
      : run.transcript;
    await ctx.db.patch(runId, { status, transcript, updatedAt: Date.now() });
  },
});

/** PUBLIC: the live run the UI subscribes to. */
export const getRun = query({
  args: { runId: v.id("runs") },
  handler: async (ctx, { runId }) => {
    return await ctx.db.get(runId);
  },
});

// ---------------------------------------------------------------------------
// public read panels for the UI
// ---------------------------------------------------------------------------

/** PUBLIC: most-recent documents (name + size only) for the side panel. */
export const listAllDocuments = query({
  args: {},
  handler: async (ctx) => {
    const docs = await ctx.db.query("documents").collect();
    return docs
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, 50)
      .map((d) => ({
        _id: d._id,
        name: d.name,
        updatedAt: d.updatedAt,
        chars: d.content.length,
      }));
  },
});

/** PUBLIC: most-recent tasks for the side panel. */
export const listAllTasks = query({
  args: {},
  handler: async (ctx) => {
    const tasks = await ctx.db.query("tasks").collect();
    return tasks.sort((a, b) => b.createdAt - a.createdAt).slice(0, 50);
  },
});
