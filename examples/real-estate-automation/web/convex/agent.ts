"use node";
// Purpose: the runAgent action and its worker. runAgent returns a runId
// immediately (so the UI can subscribe live); executeRun runs the BYOK Anthropic
// tool loop and streams transcript events into the run row via internal mutations.

import { action, internalAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";
import Anthropic from "@anthropic-ai/sdk";
import { config } from "../lib/config";
import {
  buildAnthropicTools,
  dispatchTool,
  validateConfigTools,
} from "../lib/tools";

// Safety cap so a misbehaving model can never loop forever.
const MAX_ROUNDS = 16;

/**
 * Public entry the UI calls. Validates the contract, checks the BYOK key, creates
 * the run row, and schedules the worker. Returns the runId right away so the
 * client can `useQuery(api.store.getRun, { runId })` and watch the run live.
 *
 * Note: a Convex action cannot stream over HTTP, so live UX comes from the worker
 * writing incremental events into the `runs` table (see convex/store.ts). The
 * httpAction in convex/http.ts is the alternative true-SSE path.
 */
export const runAgent = action({
  args: {
    sessionId: v.string(),
    task: v.string(),
    model: v.optional(v.string()),
  },
  handler: async (ctx, { sessionId, task, model }) => {
    // Fail loudly if the contract references a handler the dispatcher doesn't have.
    validateConfigTools(config);

    // BYOK: confirm the user's key exists for this session before we start.
    const apiKey: string | null = await ctx.runQuery(internal.keys.getApiKey, {
      sessionId,
    });
    if (!apiKey) {
      throw new Error(
        "No Anthropic API key is stored for this session. Paste your key in the " +
          "UI (it is saved per anonymous session) and run again.",
      );
    }

    const runId = await ctx.runMutation(internal.store.createRun, {
      sessionId,
      task,
    });

    // Kick off the long-running loop without blocking this call.
    await ctx.scheduler.runAfter(0, internal.agent.executeRun, {
      runId,
      sessionId,
      task,
      model,
    });

    return runId;
  },
});

/**
 * The actual tool loop. Reads the BYOK key fresh, runs Anthropic with streaming,
 * appends transcript events as it goes, and marks the run done/error.
 */
export const executeRun = internalAction({
  args: {
    runId: v.id("runs"),
    sessionId: v.string(),
    task: v.string(),
    model: v.optional(v.string()),
  },
  handler: async (ctx, { runId, sessionId, task, model }) => {
    try {
      const apiKey: string | null = await ctx.runQuery(internal.keys.getApiKey, {
        sessionId,
      });
      if (!apiKey) {
        throw new Error("The API key was cleared before the run could start.");
      }

      const client = new Anthropic({ apiKey });
      // input_schema is plain JSON Schema; the SDK's stricter type is a superset.
      const tools = buildAnthropicTools(config) as unknown as Anthropic.Tool[];
      const chosenModel = model ?? config.model;
      const messages: Anthropic.MessageParam[] = [
        { role: "user", content: task },
      ];

      for (let round = 0; round < MAX_ROUNDS; round++) {
        // Stream this assistant turn, flushing text deltas into the transcript.
        const stream = client.messages.stream({
          model: chosenModel,
          max_tokens: 4096,
          system: config.systemPrompt,
          tools,
          messages,
        });

        let buffer = "";
        let sinceFlush = 0;
        for await (const event of stream) {
          if (
            event.type === "content_block_delta" &&
            event.delta.type === "text_delta"
          ) {
            buffer += event.delta.text;
            // Batch a few deltas per write to stay live without spamming the DB.
            if (++sinceFlush >= 4) {
              await ctx.runMutation(internal.store.appendAssistantDelta, {
                runId,
                delta: buffer,
              });
              buffer = "";
              sinceFlush = 0;
            }
          }
        }
        if (buffer) {
          await ctx.runMutation(internal.store.appendAssistantDelta, {
            runId,
            delta: buffer,
          });
        }

        const response = await stream.finalMessage();
        // Feed the full assistant turn back into the conversation.
        messages.push({
          role: "assistant",
          content: response.content as Anthropic.ContentBlockParam[],
        });

        if (response.stop_reason !== "tool_use") {
          await ctx.runMutation(internal.store.setRunStatus, {
            runId,
            status: "done",
          });
          return;
        }

        // Execute each requested tool, recording the call and result, then loop.
        const toolUses = response.content.filter(
          (b): b is Anthropic.ToolUseBlock => b.type === "tool_use",
        );
        const toolResults: Anthropic.ToolResultBlockParam[] = [];
        for (const block of toolUses) {
          await ctx.runMutation(internal.store.appendRunEvent, {
            runId,
            event: { type: "tool_call", name: block.name, input: block.input },
          });
          const resultText = await dispatchTool(
            block.name,
            (block.input ?? {}) as Record<string, unknown>,
            ctx,
          );
          await ctx.runMutation(internal.store.appendRunEvent, {
            runId,
            event: {
              type: "tool_result",
              name: block.name,
              content: resultText,
            },
          });
          toolResults.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: resultText,
          });
        }
        messages.push({ role: "user", content: toolResults });
      }

      // Reached the round cap without a natural stop.
      await ctx.runMutation(internal.store.setRunStatus, {
        runId,
        status: "done",
      });
    } catch (err) {
      await ctx.runMutation(internal.store.setRunStatus, {
        runId,
        status: "error",
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
});
