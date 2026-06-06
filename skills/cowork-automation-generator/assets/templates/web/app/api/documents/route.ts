// Flat documents API — list, read (?name=), or write (POST ?name=). No [param] folders.
import { NextRequest } from "next/server";
import { listDocuments, readDoc, writeDoc } from "@/lib/store";

export const runtime = "nodejs";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest) {
  const name = req.nextUrl.searchParams.get("name");
  if (!name) return json({ documents: listDocuments() });
  const doc = readDoc(name);
  if (doc === null) return json({ error: `no document '${name}'` }, 404);
  return new Response(doc, {
    status: 200,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

export async function POST(req: NextRequest) {
  const name = req.nextUrl.searchParams.get("name") || "";
  if (!name) return json({ error: "name is required" }, 400);
  let content = "";
  try {
    const b = await req.json();
    content = typeof b?.content === "string" ? b.content : "";
  } catch {
    content = await req.text();
  }
  try {
    return json({ path: writeDoc(name, content) }, 201);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : String(e) }, 400);
  }
}
