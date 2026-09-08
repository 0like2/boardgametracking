import { NextResponse } from "next/server";

import {
  adminUpdateError,
  isAzitAdmin,
  type AdminBookingUpdate,
} from "@/lib/azit-admin";
import type { AdminBooking, BookingStatus } from "@/lib/azit";
import { SOCIAL } from "@/lib/site";
import { serverSupabase } from "@/lib/supabase";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SELECT = "id, start_at, end_at, status, name, contact, party_size, monthly_pass_count, monthly_member_name, parking, games, note, needs_night_notice, needs_host, created_at, member_verified, host_confirmed, parking_confirmed";
const STATUSES: BookingStatus[] = ["pending", "approved", "declined", "done"];

export async function GET() {
  if (!SOCIAL) return new NextResponse(null, { status: 404 });
  if (!(await isAzitAdmin())) return forbidden();
  const supabase = serverSupabase();
  if (!supabase) return unavailable();

  const now = new Date().toISOString();
  const { data: active, error: activeError } = await supabase
    .from("space_bookings")
    .select(SELECT)
    .or(`status.eq.pending,end_at.gte.${now}`)
    .order("start_at", { ascending: true })
    .range(0, 999);
  if (activeError || active?.length === 1000) {
    console.error("[azit/admin] active query failed or exceeded limit:", activeError?.code ?? "limit");
    return unavailable();
  }
  const { data: history, error: historyError } = await supabase
    .from("space_bookings")
    .select(SELECT)
    .neq("status", "pending")
    .lt("end_at", now)
    .order("end_at", { ascending: false })
    .limit(100);
  if (historyError) {
    console.error("[azit/admin] history query failed:", historyError.code ?? "unknown");
    return unavailable();
  }
  const bookings = [...((active ?? []) as AdminBooking[])];
  const ids = new Set(bookings.map((booking) => booking.id));
  for (const booking of (history ?? []) as AdminBooking[]) {
    if (!ids.has(booking.id)) bookings.push(booking);
  }
  return NextResponse.json({ bookings }, { headers: { "Cache-Control": "no-store" } });
}

export async function PATCH(request: Request) {
  if (!SOCIAL) return new NextResponse(null, { status: 404 });
  if (!(await isAzitAdmin())) return forbidden();
  if (!sameOrigin(request)) return NextResponse.json({ error: "허용되지 않은 요청입니다." }, { status: 403 });
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") {
    return NextResponse.json({ error: "JSON 형식으로 요청해주세요." }, { status: 415 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }
  const parsed = adminBody(body);
  if (!parsed) return NextResponse.json({ error: "변경 내용을 다시 확인해주세요." }, { status: 400 });
  const supabase = serverSupabase();
  if (!supabase) return unavailable();

  const { data: current, error: readError } = await supabase
    .from("space_bookings")
    .select(SELECT)
    .eq("id", parsed.id)
    .maybeSingle();
  if (readError) {
    console.error("[azit/admin] booking read failed:", readError.code ?? "unknown");
    return unavailable();
  }
  if (!current) return NextResponse.json({ error: "예약을 찾을 수 없습니다." }, { status: 404 });

  const booking = current as AdminBooking;
  const update: AdminBookingUpdate = parsed;
  const validationError = adminUpdateError(booking, update);
  if (validationError) return NextResponse.json({ error: validationError }, { status: 409 });

  const { data, error } = await supabase
    .from("space_bookings")
    .update({
      status: update.status,
      member_verified: update.memberVerified,
      host_confirmed: update.hostConfirmed,
      parking_confirmed: update.parkingConfirmed,
    })
    .eq("id", parsed.id)
    .eq("status", booking.status)
    .select(SELECT)
    .maybeSingle();
  if (error) {
    console.error("[azit/admin] update failed:", error.code ?? "unknown");
    return unavailable();
  }
  if (!data) return NextResponse.json({ error: "다른 관리자가 먼저 변경했습니다. 새로고침해주세요." }, { status: 409 });
  return NextResponse.json({ booking: data as AdminBooking });
}

function adminBody(body: unknown): ({ id: string } & AdminBookingUpdate) | null {
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;
  const value = body as Record<string, unknown>;
  if (
    typeof value.id !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.id) ||
    typeof value.status !== "string" ||
    !STATUSES.includes(value.status as BookingStatus) ||
    typeof value.memberVerified !== "boolean" ||
    typeof value.hostConfirmed !== "boolean" ||
    typeof value.parkingConfirmed !== "boolean"
  ) return null;
  return {
    id: value.id,
    status: value.status as BookingStatus,
    memberVerified: value.memberVerified,
    hostConfirmed: value.hostConfirmed,
    parkingConfirmed: value.parkingConfirmed,
  };
}

function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  return !origin || origin === new URL(request.url).origin;
}

function forbidden() {
  return NextResponse.json({ error: "관리자 권한이 필요합니다." }, { status: 403 });
}

function unavailable() {
  return NextResponse.json({ error: "예약 정보를 처리할 수 없습니다. 잠시 후 다시 시도해주세요." }, { status: 503 });
}
