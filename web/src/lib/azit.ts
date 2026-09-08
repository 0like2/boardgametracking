export type BookingStatus = "pending" | "approved" | "declined" | "done";

export type AvailabilityBooking = {
  id: string;
  start_at: string;
  end_at: string;
  status: BookingStatus;
};

export type BookingInput = {
  startAt: string;
  endAt: string;
  name: string;
  contact: string;
  partySize: number;
  monthlyPassCount: number;
  monthlyMemberName: string;
  parking: number;
  games: string;
  note: string;
  rulesAccepted: boolean;
  nightNoticeAccepted: boolean;
  hostPresenceRequested: boolean;
  website?: string;
};

export type AdminBooking = AvailabilityBooking & {
  name: string;
  contact: string;
  party_size: number;
  monthly_pass_count: number;
  monthly_member_name: string;
  parking: number;
  games: string;
  note: string;
  needs_night_notice: boolean;
  needs_host: boolean;
  created_at: string;
  member_verified: boolean;
  host_confirmed: boolean;
  parking_confirmed: boolean;
};

export type AdminBookingUpdate = {
  status: BookingStatus;
  memberVerified: boolean;
  hostConfirmed: boolean;
  parkingConfirmed: boolean;
};

export const STATUS_LABEL: Record<BookingStatus, string> = {
  pending: "예약 접수중",
  approved: "예약 확정",
  declined: "예약 취소",
  done: "이용 완료",
};

export const STATUS_CLASS: Record<BookingStatus, string> = {
  pending: "bg-weight/15 text-weight",
  approved: "bg-accent/15 text-accent",
  declined: "bg-panel-2 text-ink-dim line-through",
  done: "bg-rating/15 text-rating",
};

const KST_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;
const NIGHT_END = "09:00";
const HOST_START = "00:10";
const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?(Z|[+-]\d{2}:\d{2})$/;
const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function kstDate(date: Date): string {
  return new Date(date.getTime() + KST_MS).toISOString().slice(0, 10);
}

export function addDays(date: string, days: number): string {
  const parts = validDateParts(date);
  if (!parts || !Number.isInteger(days)) throw new RangeError("잘못된 날짜입니다.");
  return new Date(Date.UTC(parts.year, parts.month - 1, parts.day) + days * DAY_MS)
    .toISOString()
    .slice(0, 10);
}

export function toKstIso(date: string, time: string): string {
  if (!validDateParts(date) || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time)) {
    throw new RangeError("잘못된 날짜 또는 시간입니다.");
  }
  return `${date}T${time}:00+09:00`;
}

export function blockedIntervals(date: string): Array<{ start_at: string; end_at: string }> {
  const parts = validDateParts(date);
  if (!parts) return [];
  const weekday = new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay();
  const times: Record<number, [string, string]> = {
    0: ["09:00", "12:00"],
    1: ["18:00", "22:00"],
    2: ["18:00", "22:00"],
    6: ["09:00", "19:00"],
  };
  const blocked = times[weekday];
  return blocked
    ? [{ start_at: toKstIso(date, blocked[0]), end_at: toKstIso(date, blocked[1]) }]
    : [];
}

export function overlaps(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
  return Date.parse(aStart) < Date.parse(bEnd) && Date.parse(aEnd) > Date.parse(bStart);
}

export function bookingNightRequirements(
  startAt: string,
  endAt: string,
): { needsNightNotice: boolean; needsHost: boolean } {
  const start = new Date(startAt);
  const end = new Date(endAt);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || start >= end) {
    return { needsNightNotice: false, needsHost: false };
  }

  let needsNightNotice = false;
  let needsHost = false;
  const lastDate = kstDate(new Date(end.getTime() - 1));
  for (let date = kstDate(start); date <= lastDate; date = addDays(date, 1)) {
    const midnight = toKstIso(date, "00:00");
    const hostStart = toKstIso(date, HOST_START);
    const nightEnd = toKstIso(date, NIGHT_END);
    needsNightNotice ||= overlaps(startAt, endAt, midnight, nightEnd);
    needsHost ||= Date.parse(startAt) < Date.parse(nightEnd) && Date.parse(endAt) > Date.parse(hostStart);
  }

  // Ending exactly at midnight does not use the next day; going beyond it does.
  needsNightNotice ||= kstDate(start) !== lastDate;
  return { needsNightNotice, needsHost };
}

export function validateBooking(
  input: unknown,
  now = new Date(),
): { value: BookingInput | null; error: string | null } {
  if (!input || typeof input !== "object" || Array.isArray(input)) return invalid("잘못된 요청입니다.");
  const body = input as Record<string, unknown>;
  const startAt = timestamp(body.startAt);
  const endAt = timestamp(body.endAt);
  if (!startAt || !endAt) return invalid("날짜와 시간을 다시 확인해주세요.");

  const startMs = Date.parse(startAt);
  const endMs = Date.parse(endAt);
  if (endMs <= startMs) return invalid("종료 시간은 시작 시간보다 늦어야 합니다.");
  if (endMs - startMs > DAY_MS) return invalid("한 번에 최대 24시간까지 예약할 수 있습니다.");
  if (startMs < now.getTime()) return invalid("지난 시간은 예약할 수 없습니다.");
  if (kstDate(new Date(startMs)) > addDays(kstDate(now), 90)) {
    return invalid("예약은 90일 전부터 신청할 수 있습니다.");
  }
  if (startMs % 600_000 !== 0 || endMs % 600_000 !== 0) {
    return invalid("예약 시간은 10분 단위로 선택해주세요.");
  }

  const lastDate = kstDate(new Date(endMs - 1));
  for (let date = kstDate(new Date(startMs)); date <= lastDate; date = addDays(date, 1)) {
    if (blockedIntervals(date).some((slot) => overlaps(startAt, endAt, slot.start_at, slot.end_at))) {
      return invalid("해당 시간은 정기 이용 시간이라 예약할 수 없습니다.");
    }
  }

  const name = text(body.name, 100);
  const contact = text(body.contact, 200);
  const monthlyMemberName = text(body.monthlyMemberName, 100);
  const games = text(body.games, 500);
  const note = text(body.note, 1000);
  if (!name || !contact || !monthlyMemberName) {
    return invalid("이름, 연락처, 월 이용권 사용자 이름을 입력해주세요.");
  }
  if (/^(?:당근|카카오톡|전화|연락처)$/i.test(contact)) {
    return invalid("연락 가능한 아이디나 전화번호를 입력해주세요.");
  }

  const partySize = integer(body.partySize);
  const monthlyPassCount = integer(body.monthlyPassCount);
  const parking = integer(body.parking);
  if (!partySize || partySize < 1 || partySize > 50) return invalid("이용 인원을 확인해주세요.");
  if (!monthlyPassCount || monthlyPassCount < 1 || monthlyPassCount > partySize) {
    return invalid("월 이용권 사용자가 1명 이상 있어야 합니다.");
  }
  if (parking === null || parking < 0 || parking > 2) return invalid("주차 요청은 0~2대로 선택해주세요.");
  if (body.rulesAccepted !== true) return invalid("이용 및 뒷정리 규칙에 동의해주세요.");

  const night = bookingNightRequirements(startAt, endAt);
  if (night.needsNightNotice && body.nightNoticeAccepted !== true) {
    return invalid("심야 이용 안내를 확인해주세요.");
  }
  if (night.needsHost && body.hostPresenceRequested !== true) {
    return invalid("00:10~09:00 이용은 관리자 동행 요청이 필요합니다.");
  }

  return {
    value: {
      startAt,
      endAt,
      name,
      contact,
      partySize,
      monthlyPassCount,
      monthlyMemberName,
      parking,
      games,
      note,
      rulesAccepted: true,
      nightNoticeAccepted: body.nightNoticeAccepted === true,
      hostPresenceRequested: body.hostPresenceRequested === true,
      website: text(body.website, 200),
    },
    error: null,
  };
}

export function adminUpdateError(
  booking: AdminBooking,
  update: AdminBookingUpdate,
  now = new Date(),
): string | null {
  const allowed =
    booking.status === "pending"
      ? ["pending", "approved", "declined"]
      : booking.status === "approved"
        ? ["approved", "declined", "done"]
        : [];
  if (!allowed.includes(update.status)) return "현재 상태에서는 요청한 상태로 변경할 수 없습니다.";
  if (update.status === "approved") {
    if (Date.parse(booking.end_at) <= now.getTime()) return "이미 종료된 예약은 승인할 수 없습니다.";
    if (!update.memberVerified) return "월 이용권 사용자를 먼저 확인해주세요.";
    if (booking.needs_host && !update.hostConfirmed) return "심야 관리자 동행을 먼저 확인해주세요.";
    if (booking.parking > 0 && !update.parkingConfirmed) return "주차 가능 여부를 먼저 확인해주세요.";
  }
  if (update.status === "done" && Date.parse(booking.end_at) > now.getTime()) {
    return "이용 종료 전에는 완료 처리할 수 없습니다.";
  }
  return null;
}

function validDateParts(date: string): { year: number; month: number; day: number } | null {
  const match = DATE_RE.exec(date);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const check = new Date(Date.UTC(year, month - 1, day));
  return check.getUTCFullYear() === year && check.getUTCMonth() === month - 1 && check.getUTCDate() === day
    ? { year, month, day }
    : null;
}

function timestamp(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = ISO_RE.exec(value);
  if (!match || !validDateParts(`${match[1]}-${match[2]}-${match[3]}`)) return null;
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6] ?? 0);
  const parsed = Date.parse(value);
  if (
    hour > 23 ||
    minute > 59 ||
    second > 59 ||
    !Number.isFinite(parsed)
  ) return null;
  return value;
}

function text(value: unknown, max: number): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function integer(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) ? value : null;
}

function invalid(error: string): { value: null; error: string } {
  return { value: null, error };
}
