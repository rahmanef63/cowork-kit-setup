// Flat records API — no dynamic [param] folders (keeps the .skill zip path-safe on
// all OSes). `table` and `id` come from the query string; bodies are JSON.
import { NextRequest } from "next/server";
import { listRecords, createRecord, updateRecord, deleteRecord } from "@/lib/store";

export const runtime = "nodejs";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest) {
  const table = req.nextUrl.searchParams.get("table") || "";
  const q = req.nextUrl.searchParams.get("q") || "";
  if (!table) return json({ error: "table is required" }, 400);
  try {
    return json({ records: listRecords(table, q) });
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : String(e) }, 500);
  }
}

export async function POST(req: NextRequest) {
  const table = req.nextUrl.searchParams.get("table") || "";
  if (!table) return json({ error: "table is required" }, 400);
  let data: unknown;
  try {
    data = await req.json();
  } catch {
    return json({ error: "body must be JSON" }, 400);
  }
  try {
    return json({ record: createRecord(table, data as Record<string, unknown>) }, 201);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : String(e) }, 400);
  }
}

export async function PUT(req: NextRequest) {
  const table = req.nextUrl.searchParams.get("table") || "";
  const id = req.nextUrl.searchParams.get("id") || "";
  if (!table || !id) return json({ error: "table and id are required" }, 400);
  let data: unknown;
  try {
    data = await req.json();
  } catch {
    return json({ error: "body must be JSON" }, 400);
  }
  try {
    const rec = updateRecord(table, id, data as Record<string, unknown>);
    return rec ? json({ record: rec }) : json({ error: `no record '${id}' in '${table}'` }, 404);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : String(e) }, 400);
  }
}

export async function DELETE(req: NextRequest) {
  const table = req.nextUrl.searchParams.get("table") || "";
  const id = req.nextUrl.searchParams.get("id") || "";
  if (!table || !id) return json({ error: "table and id are required" }, 400);
  return deleteRecord(table, id)
    ? json({ ok: true })
    : json({ error: `no record '${id}' in '${table}'` }, 404);
}
