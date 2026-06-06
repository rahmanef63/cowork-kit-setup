// Purpose: Convex table definitions for the BYOK automation webapp.

import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Per-session BYOK Anthropic key. One row per anonymous session.
  // SECURITY: stored as plaintext for this template. See README for hardening notes.
  apiKeys: defineTable({
    sessionId: v.string(),
    key: v.string(),
    createdAt: v.number(),
  }).index("by_session", ["sessionId"]),

  // Deliverables the agent writes (the Convex equivalent of ./output files).
  documents: defineTable({
    name: v.string(),
    content: v.string(),
    updatedAt: v.number(),
  }).index("by_name", ["name"]),

  // Lightweight CRM/log rows the agent saves, grouped by logical table name.
  records: defineTable({
    table: v.string(),
    data: v.any(),
    createdAt: v.number(),
  }).index("by_table", ["table"]),

  // Follow-up tasks the agent creates.
  tasks: defineTable({
    title: v.string(),
    due: v.optional(v.string()),
    notes: v.optional(v.string()),
    done: v.boolean(),
    createdAt: v.number(),
  }),

  // One agent run. `transcript` is an append-only event log the UI subscribes to.
  // Each event is an object with a `type` discriminator, e.g.:
  //   { type: "assistant",   text: string }
  //   { type: "tool_call",   name: string, input: unknown }
  //   { type: "tool_result", name: string, content: string }
  //   { type: "error",       message: string }
  runs: defineTable({
    sessionId: v.string(),
    task: v.string(),
    status: v.union(
      v.literal("running"),
      v.literal("done"),
      v.literal("error"),
    ),
    transcript: v.array(v.any()),
    createdAt: v.number(),
    updatedAt: v.number(),
  }).index("by_session", ["sessionId"]),
});
