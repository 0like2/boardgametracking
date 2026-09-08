import assert from "node:assert/strict";
import test from "node:test";

import {
  addDays,
  adminUpdateError,
  blockedIntervals,
  bookingNightRequirements,
  kstDate,
  overlaps,
  toKstIso,
  validateBooking,
  type BookingInput,
  type AdminBooking,
} from "../src/lib/azit.ts";

const now = new Date("2026-09-09T00:00:00+09:00");
const valid: BookingInput = {
  startAt: toKstIso("2026-09-16", "10:00"),
  endAt: toKstIso("2026-09-16", "12:00"),
  name: "신청자",
  contact: "010-0000-0000",
  partySize: 4,
  monthlyPassCount: 1,
  monthlyMemberName: "월회원",
  parking: 1,
  games: "아크 노바",
  note: "",
  rulesAccepted: true,
  nightNoticeAccepted: false,
  hostPresenceRequested: false,
};

test("KST date helpers preserve calendar dates", () => {
  assert.equal(kstDate(new Date("2026-09-15T15:00:00Z")), "2026-09-16");
  assert.equal(addDays("2026-02-28", 1), "2026-03-01");
  assert.equal(toKstIso("2026-09-16", "00:10"), "2026-09-16T00:10:00+09:00");
  assert.throws(() => toKstIso("2026-02-30", "10:00"));
});

test("weekly blocked hours use KST weekdays", () => {
  assert.deepEqual(blockedIntervals("2026-09-14"), [{
    start_at: toKstIso("2026-09-14", "18:00"),
    end_at: toKstIso("2026-09-14", "22:00"),
  }]);
  assert.equal(blockedIntervals("2026-09-15")[0].start_at, toKstIso("2026-09-15", "18:00"));
  assert.equal(blockedIntervals("2026-09-19")[0].end_at, toKstIso("2026-09-19", "19:00"));
  assert.equal(blockedIntervals("2026-09-20")[0].end_at, toKstIso("2026-09-20", "12:00"));
  assert.deepEqual(blockedIntervals("2026-09-16"), []);
});

test("half-open intervals allow adjacent reservations", () => {
  assert.equal(overlaps(
    toKstIso("2026-09-16", "10:00"),
    toKstIso("2026-09-16", "11:00"),
    toKstIso("2026-09-16", "11:00"),
    toKstIso("2026-09-16", "12:00"),
  ), false);
  assert.equal(overlaps(
    toKstIso("2026-09-16", "10:00"),
    toKstIso("2026-09-16", "11:10"),
    toKstIso("2026-09-16", "11:00"),
    toKstIso("2026-09-16", "12:00"),
  ), true);
});

test("night rules honor the 00:10 and 09:00 boundaries", () => {
  assert.deepEqual(bookingNightRequirements(
    toKstIso("2026-09-16", "23:00"),
    toKstIso("2026-09-17", "00:10"),
  ), { needsNightNotice: true, needsHost: false });
  assert.deepEqual(bookingNightRequirements(
    toKstIso("2026-09-17", "00:10"),
    toKstIso("2026-09-17", "00:20"),
  ), { needsNightNotice: true, needsHost: true });
  assert.deepEqual(bookingNightRequirements(
    toKstIso("2026-09-17", "09:00"),
    toKstIso("2026-09-17", "10:00"),
  ), { needsNightNotice: false, needsHost: false });
});

test("validates membership and rejects malformed dates and types", () => {
  assert.equal(validateBooking(valid, now).error, null);
  assert.equal(validateBooking({ ...valid, startAt: new Date(valid.startAt).toISOString() }, now).error, null);
  assert.match(validateBooking({ ...valid, startAt: "2026-09-16T10:00:59+09:00" }, now).error ?? "", /10분/);
  assert.match(validateBooking({ ...valid, startAt: "2026-09-16T10:00:00.001+09:00" }, now).error ?? "", /10분/);
  assert.match(validateBooking({ ...valid, startAt: "2026-02-30T10:00:00+09:00" }, now).error ?? "", /날짜/);
  assert.match(validateBooking({ ...valid, partySize: "4" }, now).error ?? "", /인원/);
  assert.match(validateBooking({ ...valid, contact: "카카오톡" }, now).error ?? "", /아이디나 전화번호/);
  assert.match(validateBooking({ ...valid, monthlyPassCount: 0 }, now).error ?? "", /월 이용권/);
  assert.match(validateBooking({ ...valid, monthlyPassCount: 5 }, now).error ?? "", /월 이용권/);
  assert.match(validateBooking({ ...valid, monthlyMemberName: "" }, now).error ?? "", /월 이용권 사용자/);
});

test("rejects blocked crossings including overnight ranges", () => {
  const blocked = {
    ...valid,
    startAt: toKstIso("2026-09-15", "21:50"),
    endAt: toKstIso("2026-09-16", "00:10"),
    nightNoticeAccepted: true,
  };
  assert.match(validateBooking(blocked, now).error ?? "", /정기 이용/);
});

test("requires night acknowledgements and accepts an explicit cross-midnight end date", () => {
  const night = {
    ...valid,
    startAt: toKstIso("2026-09-16", "23:00"),
    endAt: toKstIso("2026-09-17", "01:00"),
  };
  assert.match(validateBooking(night, now).error ?? "", /심야 이용 안내/);
  assert.match(validateBooking({ ...night, nightNoticeAccepted: true }, now).error ?? "", /관리자 동행/);
  assert.equal(validateBooking({
    ...night,
    nightNoticeAccepted: true,
    hostPresenceRequested: true,
  }, now).error, null);
});

test("admin approval enforces confirmations, expiry, and terminal states", () => {
  const booking: AdminBooking = {
    id: "00000000-0000-4000-8000-000000000001",
    start_at: toKstIso("2026-09-16", "00:20"),
    end_at: toKstIso("2026-09-16", "02:00"),
    status: "pending",
    name: "신청자",
    contact: "010",
    party_size: 2,
    monthly_pass_count: 1,
    monthly_member_name: "월회원",
    parking: 1,
    games: "",
    note: "",
    needs_night_notice: true,
    needs_host: true,
    created_at: now.toISOString(),
    member_verified: false,
    host_confirmed: false,
    parking_confirmed: false,
  };
  const confirmations = {
    status: "approved" as const,
    memberVerified: true,
    hostConfirmed: true,
    parkingConfirmed: true,
  };
  assert.match(adminUpdateError(booking, { ...confirmations, memberVerified: false }, now) ?? "", /월 이용권/);
  assert.match(adminUpdateError(booking, { ...confirmations, hostConfirmed: false }, now) ?? "", /동행/);
  assert.match(adminUpdateError(booking, { ...confirmations, parkingConfirmed: false }, now) ?? "", /주차/);
  assert.equal(adminUpdateError(booking, confirmations, now), null);
  assert.equal(adminUpdateError(booking, { ...confirmations, status: "pending" }, now), null);
  assert.match(adminUpdateError(booking, confirmations, new Date("2026-09-17T00:00:00+09:00")) ?? "", /종료/);
  assert.match(adminUpdateError({ ...booking, status: "done" }, { ...confirmations, status: "declined" }, now) ?? "", /현재 상태/);
});
