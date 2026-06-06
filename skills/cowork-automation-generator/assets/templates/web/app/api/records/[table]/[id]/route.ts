// /api/records/[table]/[id]
//   PUT  body = fields  — merge-update a record by id
//   DELETE              — delete a record by id

import { NextRequest, NextResponse } from "next/server";
import { updateRecord, deleteRecord } from "@/lib/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function PUT(
  req: NextRequest,
  { params }: { params: { table: string; id: string } },
) {
  try {
    const body = await req.json().catch(() => null);
    if (body === null || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json(
        { error: "Request body must be a JSON object of fields." },
        { status: 400 },
      );
    }
    const record = updateRecord(
      params.table,
      params.id,
      body as Record<string, unknown>,
    );
    if (!record) {
      return NextResponse.json(
        { error: `No record '${params.id}' in '${params.table}'.` },
        { status: 404 },
      );
    }
    return NextResponse.json({ record });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 400 },
    );
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { table: string; id: string } },
) {
  try {
    const ok = deleteRecord(params.table, params.id);
    if (!ok) {
      return NextResponse.json(
        { error: `No record '${params.id}' in '${params.table}'.` },
        { status: 404 },
      );
    }
    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}
