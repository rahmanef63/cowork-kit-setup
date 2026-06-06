// /api/records/[table]
//   GET  ?q=<substring>  — list (and optionally search) records in a table
//   POST  body = fields  — create a record

import { NextRequest, NextResponse } from "next/server";
import { listRecords, createRecord } from "@/lib/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: { table: string } },
) {
  try {
    const q = req.nextUrl.searchParams.get("q") ?? "";
    return NextResponse.json({ records: listRecords(params.table, q) });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: { table: string } },
) {
  try {
    const body = await req.json().catch(() => null);
    if (body === null || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json(
        { error: "Request body must be a JSON object of fields." },
        { status: 400 },
      );
    }
    const record = createRecord(params.table, body as Record<string, unknown>);
    return NextResponse.json({ record }, { status: 201 });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 400 },
    );
  }
}
