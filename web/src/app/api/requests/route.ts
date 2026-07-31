import { NextResponse } from "next/server";

import { type AppRequest, notify } from "@/lib/notify";
import { serverSupabase } from "@/lib/supabase";

export const runtime = "nodejs";

const MAX_FIELD = 500;

/**
 * In-memory throttle. Good enough to stop an accidental double-tap or a bored
 * visitor spamming the webhook; it resets on cold start, which is fine because
 * the only cost of a miss is one extra Discord message.
 */
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const hits = new Map<string, number[]>();

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < RATE_WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);

  if (hits.size > 5000) hits.clear();
  return recent.length > RATE_LIMIT;
}

function str(v: unknown): string {
  return typeof v === "string" ? v.trim().slice(0, MAX_FIELD) : "";
}

function parse(body: Record<string, unknown>): AppRequest | null {
  const name = str(body.name);
  const contact = str(body.contact);
  if (!name || !contact) return null;

  if (body.type === "rental") {
    const gameName = str(body.gameName);
    if (!gameName) return null;
    return {
      type: "rental",
      name,
      contact,
      gameName,
      gameSlug: str(body.gameSlug),
      pickupDate: str(body.pickupDate),
      returnDate: str(body.returnDate),
      note: str(body.note),
    };
  }

  if (body.type === "meetup") {
    // Only availability is asked for — the host picks the actual date and place.
    return {
      type: "meetup",
      name,
      contact,
      days: str(body.days),
      games: str(body.games),
    };
  }

  return null;
}

export async function POST(request: Request) {
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";

  if (rateLimited(ip)) {
    return NextResponse.json(
      { error: "잠시 후 다시 시도해주세요. (요청이 너무 잦습니다)" },
      { status: 429 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }

  // Honeypot: real people leave this hidden field empty.
  if (str(body.website)) {
    return NextResponse.json({ ok: true, delivered: [] });
  }

  const req = parse(body);
  if (!req) {
    return NextResponse.json(
      { error: "이름, 연락처와 필수 항목을 채워주세요." },
      { status: 400 },
    );
  }

  const supabase = serverSupabase();
  if (supabase) {
    const { error } = await supabase.from("requests").insert({
      type: req.type,
      name: req.name,
      contact: req.contact,
      payload: req,
    });
    if (error) console.error("[requests] supabase insert failed:", error.message);
  }

  const { delivered, failed } = await notify(req);

  // Never tell a visitor "전달됐습니다" when the request went nowhere. With no
  // channel configured and no database, the submission would vanish silently.
  if (delivered.length === 0 && !supabase) {
    console.error(
      "[requests] dropped — configure DISCORD_WEBHOOK_URL, RESEND_API_KEY, or Supabase",
    );
    return NextResponse.json(
      { error: "지금은 신청을 받을 수 없습니다. 직접 연락 부탁드립니다." },
      { status: 503 },
    );
  }

  if (delivered.length === 0 && failed.length > 0) {
    return NextResponse.json(
      { error: "알림 전송에 실패했습니다. 직접 연락 부탁드립니다." },
      { status: 502 },
    );
  }

  return NextResponse.json({ ok: true, delivered, failed });
}
