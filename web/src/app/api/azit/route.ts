import { NextResponse } from "next/server";

import {
  bookingNightRequirements,
  toKstIso,
  validateBooking,
  type AvailabilityBooking,
} from "@/lib/azit";
import { SOCIAL } from "@/lib/site";
import { serverSupabase } from "@/lib/supabase";
import { notify } from "@/lib/notify";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_BODY_BYTES = 8 * 1024;
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const hits = new Map<string, number[]>();
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export async function GET(request: Request) {
  if (!SOCIAL) return new NextResponse(null, { status: 404 });
  const url = new URL(request.url);
  const from = url.searchParams.get("from") ?? "";
  const to = url.searchParams.get("to") ?? "";
  const range = dateRange(from, to);
  if (!range) {
    return NextResponse.json({ error: "조회 기간을 다시 확인해주세요." }, { status: 400 });
  }

  const supabase = serverSupabase();
  if (!supabase) return unavailable();
  const bookings: AvailabilityBooking[] = [];
  for (let page = 0; page < 10; page += 1) {
    const { data, error } = await supabase
      .from("space_bookings")
      .select("id, start_at, end_at, status")
      .lt("start_at", range.end)
      .gt("end_at", range.start)
      .order("start_at", { ascending: true })
      .order("id", { ascending: true })
      .range(page * 1000, page * 1000 + 999);
    if (error) {
      console.error("[azit] availability query failed:", error.code ?? "unknown");
      return unavailable();
    }
    bookings.push(...((data ?? []) as AvailabilityBooking[]));
    if ((data?.length ?? 0) < 1000) break;
    if (page === 9) return unavailable();
  }
  return NextResponse.json(
    { bookings, updatedAt: new Date().toISOString() },
    { headers: { "Cache-Control": "no-store" } },
  );
}

export async function POST(request: Request) {
  if (!SOCIAL) return new NextResponse(null, { status: 404 });
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") {
    return NextResponse.json({ error: "JSON 형식으로 요청해주세요." }, { status: 415 });
  }
  const declaredSize = Number(request.headers.get("content-length") ?? 0);
  if (declaredSize > MAX_BODY_BYTES) return tooLarge();
  if (rateLimited(clientIp(request))) {
    return NextResponse.json({ error: "잠시 후 다시 시도해주세요." }, { status: 429 });
  }

  let body: unknown;
  try {
    const raw = await readBody(request);
    if (raw === null) return tooLarge();
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }

  if (body && typeof body === "object" && !Array.isArray(body)) {
    const website = (body as Record<string, unknown>).website;
    if (typeof website === "string" && website.trim()) return new NextResponse(null, { status: 404 });
  }

  const checked = validateBooking(body);
  if (!checked.value) return NextResponse.json({ error: checked.error }, { status: 400 });
  const value = checked.value;
  const night = bookingNightRequirements(value.startAt, value.endAt);
  const supabase = serverSupabase();
  if (!supabase) return unavailable();

  const { data, error } = await supabase
    .from("space_bookings")
    .insert({
      start_at: value.startAt,
      end_at: value.endAt,
      status: "pending",
      name: value.name,
      contact: value.contact,
      party_size: value.partySize,
      monthly_pass_count: value.monthlyPassCount,
      monthly_member_name: value.monthlyMemberName,
      parking: value.parking,
      games: value.games,
      note: value.note,
      needs_night_notice: night.needsNightNotice,
      needs_host: night.needsHost,
    })
    .select("id, start_at, end_at, status")
    .single();

  if (error) {
    if (error.code === "23P01") {
      return NextResponse.json({ error: "방금 다른 예약이 접수되었습니다. 다른 시간을 선택해주세요." }, { status: 409 });
    }
    console.error("[azit] booking insert failed:", error.code ?? "unknown");
    return unavailable();
  }
  const { delivered } = await notify({
    ...value, type: "space", bookingId: data.id, needsHost: night.needsHost,
  });
  return NextResponse.json(
    { booking: data as AvailabilityBooking, notified: delivered.includes("discord") },
    { status: 201 },
  );
}

function dateRange(from: string, to: string): { start: string; end: string } | null {
  if (!DATE_RE.test(from) || !DATE_RE.test(to)) return null;
  try {
    const start = toKstIso(from, "00:00");
    const end = toKstIso(to, "00:00");
    const days = (Date.parse(end) - Date.parse(start)) / 86_400_000;
    return days > 0 && days <= 45 ? { start, end } : null;
  } catch {
    return null;
  }
}

function clientIp(request: Request): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
}

async function readBody(request: Request): Promise<string | null> {
  if (!request.body) return "";
  const reader = request.body.getReader();
  const decoder = new TextDecoder();
  let size = 0;
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) return result + decoder.decode();
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel();
      return null;
    }
    result += decoder.decode(value, { stream: true });
  }
}

// ponytail: per-instance memory resets on cold starts; replace with a shared limiter if abuse becomes measurable.
function rateLimited(ip: string): boolean {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((time) => now - time < RATE_WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > RATE_LIMIT;
}

function tooLarge() {
  return NextResponse.json({ error: "요청 내용이 너무 깁니다." }, { status: 413 });
}

function unavailable() {
  return NextResponse.json(
    { error: "지금은 예약 정보를 불러오거나 접수할 수 없습니다. 잠시 후 다시 시도해주세요." },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}
