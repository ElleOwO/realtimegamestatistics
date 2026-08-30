import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  const configured = process.env.RTGS_MODE;
  const mode = configured === "test" || configured === "replay" ? configured : "live";
  return NextResponse.json({
    mode,
    artifact_policy: process.env.RTGS_ARTIFACT_POLICY || "compact",
  });
}
