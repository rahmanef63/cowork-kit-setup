// GET /api/documents/[name] — read one document from output/ as plain text.

import { NextRequest, NextResponse } from "next/server";
import { readDoc } from "@/lib/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: { name: string } },
) {
  try {
    const content = readDoc(decodeURIComponent(params.name));
    if (content === null) {
      return NextResponse.json(
        { error: `No document named '${params.name}'.` },
        { status: 404 },
      );
    }
    return new NextResponse(content, {
      status: 200,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 500 },
    );
  }
}
