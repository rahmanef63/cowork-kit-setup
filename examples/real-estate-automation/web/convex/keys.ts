// Purpose: store / clear / check the per-session BYOK Anthropic key.
// The public API never returns the key itself — only whether one exists.

import { mutation, query, internalQuery } from "./_generated/server";
import { v } from "convex/values";

/** Save (or replace) the Anthropic key for a session. */
export const setKey = mutation({
  args: { sessionId: v.string(), key: v.string() },
  handler: async (ctx, { sessionId, key }) => {
    const existing = await ctx.db
      .query("apiKeys")
      .withIndex("by_session", (q) => q.eq("sessionId", sessionId))
      .unique();
    if (existing) {
      await ctx.db.patch(existing._id, { key, createdAt: Date.now() });
    } else {
      await ctx.db.insert("apiKeys", { sessionId, key, createdAt: Date.now() });
    }
    return { ok: true };
  },
});

/** Remove the key for a session. */
export const clearKey = mutation({
  args: { sessionId: v.string() },
  handler: async (ctx, { sessionId }) => {
    const existing = await ctx.db
      .query("apiKeys")
      .withIndex("by_session", (q) => q.eq("sessionId", sessionId))
      .unique();
    if (existing) await ctx.db.delete(existing._id);
    return { ok: true };
  },
});

/** Whether a key is stored for this session. Never returns the key. */
export const keyStatus = query({
  args: { sessionId: v.string() },
  handler: async (ctx, { sessionId }) => {
    const existing = await ctx.db
      .query("apiKeys")
      .withIndex("by_session", (q) => q.eq("sessionId", sessionId))
      .unique();
    return { hasKey: existing !== null };
  },
});

/**
 * INTERNAL ONLY: read the raw key for the agent action at request time.
 * Not part of the public API surface, so clients can never call it.
 */
export const getApiKey = internalQuery({
  args: { sessionId: v.string() },
  handler: async (ctx, { sessionId }): Promise<string | null> => {
    const existing = await ctx.db
      .query("apiKeys")
      .withIndex("by_session", (q) => q.eq("sessionId", sessionId))
      .unique();
    return existing?.key ?? null;
  },
});
