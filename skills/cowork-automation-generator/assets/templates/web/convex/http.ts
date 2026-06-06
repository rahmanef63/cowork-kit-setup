// Purpose: an httpAction that streams Anthropic tokens over Server-Sent Events.
// This is the DOCUMENTED ALTERNATIVE to the default path (convex/agent.ts, which
// streams by writing into the `runs` table and is subscribed live via useQuery).
// Use this when you want true token-by-token HTTP streaming to a custom client.

import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import Anthropic from "@anthropic-ai/sdk";
import { config } from "../lib/config";
import { buildAnthropicTools } from "../lib/tools";

const http = httpRouter();

const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// Preflight so a browser on another origin can POST here.
http.route({
  path: "/stream-chat",
  method: "OPTIONS",
  handler: httpAction(async () => new Response(null, { headers: corsHeaders })),
});

http.route({
  path: "/stream-chat",
  method: "POST",
  handler: httpAction(async (_ctx, request) => {
    let body: { apiKey?: string; task?: string; model?: string };
    try {
      body = (await request.json()) as typeof body;
    } catch {
      return new Response("Invalid JSON body.", {
        status: 400,
        headers: corsHeaders,
      });
    }

    const { apiKey, task, model } = body;
    // BYOK: the key comes from the POST body, never from a server env var.
    if (!apiKey) {
      return new Response("Missing `apiKey` (BYOK).", {
        status: 400,
        headers: corsHeaders,
      });
    }
    if (!task) {
      return new Response("Missing `task`.", {
        status: 400,
        headers: corsHeaders,
      });
    }

    const encoder = new TextEncoder();
    const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
    const writer = writable.getWriter();
    const send = (obj: unknown) =>
      writer.write(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));

    // Stream the first assistant turn's tokens. This demo streams a single turn
    // (no tool execution) to keep the SSE example focused; the full tool loop is
    // in convex/agent.ts and surfaces live via the `runs` table subscription.
    void (async () => {
      try {
        const client = new Anthropic({ apiKey });
        const stream = client.messages.stream({
          model: model ?? config.model,
          max_tokens: 2048,
          system: config.systemPrompt,
          tools: buildAnthropicTools(config) as unknown as Anthropic.Tool[],
          messages: [{ role: "user", content: task }],
        });
        for await (const event of stream) {
          if (
            event.type === "content_block_delta" &&
            event.delta.type === "text_delta"
          ) {
            await send({ text: event.delta.text });
          }
        }
        const final = await stream.finalMessage();
        await send({ done: true, stop_reason: final.stop_reason });
      } catch (err) {
        await send({ error: err instanceof Error ? err.message : String(err) });
      } finally {
        await writer.close();
      }
    })();

    return new Response(readable, {
      headers: {
        ...corsHeaders,
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
      },
    });
  }),
});

export default http;
