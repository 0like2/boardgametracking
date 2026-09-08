"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  Car,
  Gamepad2,
  RefreshCw,
  Users,
} from "lucide-react";

import type { AdminBooking, BookingStatus } from "@/lib/azit";
import { STATUS_CLASS, STATUS_LABEL } from "@/lib/azit";
import { browserSupabase } from "@/lib/supabase-browser";

type Filter = "pending" | "approved" | "history" | "all";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "pending", label: "접수 중" },
  { value: "approved", label: "예약 확정" },
  { value: "history", label: "지난 내역" },
  { value: "all", label: "전체" },
];

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "long",
  day: "numeric",
  weekday: "short",
});
const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const moneyFormatter = new Intl.NumberFormat("ko-KR");

export function AzitAdmin() {
  const [bookings, setBookings] = useState<AdminBooking[]>([]);
  const [filter, setFilter] = useState<Filter>("pending");
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [now, setNow] = useState(0);
  const requestId = useRef(0);

  const refresh = useCallback(async (preserveMessage = false) => {
    const id = ++requestId.current;
    try {
      const response = await fetch("/api/azit/admin", { cache: "no-store" });
      const data = (await response.json()) as { bookings?: AdminBooking[]; error?: string };
      if (!response.ok || !data.bookings) {
        throw new Error(data.error || "최신 예약을 불러오지 못했습니다. 다시 시도해 주세요.");
      }
      if (id !== requestId.current) return;
      setBookings(data.bookings);
      setNow(Date.now());
      setStale(false);
      if (!preserveMessage) setMessage("");
    } catch (error) {
      if (id !== requestId.current) return;
      setStale(true);
      setMessage(
        error instanceof Error
          ? error.message
          : "최신 예약을 불러오지 못했습니다. 다시 시도해 주세요.",
      );
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    const timer = window.setInterval(() => void refresh(), 15_000);
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);

    let channel: ReturnType<ReturnType<typeof browserSupabase>["channel"]> | null = null;
    try {
      channel = browserSupabase()
        .channel("azit-availability")
        .on("broadcast", { event: "booking_changed" }, () => void refresh())
        .subscribe();
    } catch {
      // The polling fallback still keeps this page current.
    }

    return () => {
      requestId.current += 1;
      window.clearTimeout(initial);
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      void channel?.unsubscribe();
    };
  }, [refresh]);

  const counts = useMemo(
    () => ({
      pending: bookings.filter((booking) => booking.status === "pending").length,
      approved: bookings.filter((booking) => booking.status === "approved").length,
      history: bookings.filter(
        (booking) => booking.status === "declined" || booking.status === "done",
      ).length,
      all: bookings.length,
    }),
    [bookings],
  );

  const visible = useMemo(() => {
    const rows = bookings.filter((booking) => {
      if (filter === "all") return true;
      if (filter === "history") return booking.status === "declined" || booking.status === "done";
      return booking.status === filter;
    });
    return rows.sort((a, b) => {
      const pendingOrder = Number(b.status === "pending") - Number(a.status === "pending");
      return pendingOrder || Date.parse(a.start_at) - Date.parse(b.start_at);
    });
  }, [bookings, filter]);

  async function update(
    booking: AdminBooking,
    changes: Partial<
      Pick<AdminBooking, "status" | "member_verified" | "host_confirmed" | "parking_confirmed">
    >,
  ) {
    const next = { ...booking, ...changes };
    if (
      next.status === "declined" &&
      booking.status !== "declined" &&
      !window.confirm("이 예약을 취소할까요?")
    ) {
      return;
    }

    requestId.current += 1;
    setBusyId(booking.id);
    setMessage("");
    try {
      const response = await fetch("/api/azit/admin", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: booking.id,
          status: next.status,
          memberVerified: next.member_verified,
          hostConfirmed: next.host_confirmed,
          parkingConfirmed: next.parking_confirmed,
        }),
      });
      const data = (await response.json()) as { booking?: AdminBooking; error?: string };
      if (!response.ok || !data.booking) {
        throw new Error(data.error || "변경사항을 저장하지 못했습니다.");
      }
      const updatedBooking = data.booking;
      setBookings((current) =>
        current.map((item) => (item.id === booking.id ? updatedBooking : item)),
      );
      setStale(false);
      setMessage("변경사항을 저장했습니다.");
    } catch (error) {
      setStale(true);
      setMessage(
        error instanceof Error
          ? error.message
          : "변경사항을 저장하지 못했습니다. 새로고침 후 다시 시도해 주세요.",
      );
    } finally {
      requestId.current += 1;
      setBusyId(null);
      void refresh(true);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black">아지트 예약 관리</h1>
          <p className="mt-1.5 text-sm text-ink-dim">신청 내용을 확인하고 이용 조건을 점검해 주세요.</p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-panel px-3 py-2 text-sm font-bold text-ink-dim transition-colors hover:bg-panel-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50"
        >
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> 새로고침
        </button>
      </div>

      <p
        aria-live="polite"
        className={`mt-4 min-h-5 text-sm ${stale ? "text-weight" : "text-ink-dim"}`}
      >
        {message}
      </p>

      <div className="no-scrollbar mt-3 flex gap-2 overflow-x-auto pb-1" role="group" aria-label="예약 상태">
        {FILTERS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-sm font-bold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              filter === value
                ? "border-accent bg-accent text-white"
                : "border-line bg-panel text-ink-dim hover:bg-panel-2 hover:text-ink"
            }`}
          >
            {label} <span className="tnum">{counts[value]}</span>
          </button>
        ))}
      </div>

      {loading && bookings.length === 0 ? (
        <p className="mt-5 rounded-2xl border border-line bg-panel px-4 py-12 text-center text-sm text-ink-faint">
          예약을 불러오는 중입니다…
        </p>
      ) : stale && bookings.length === 0 ? (
        <p className="mt-5 rounded-2xl border border-weight/30 bg-weight/10 px-4 py-12 text-center text-sm text-weight">
          예약 정보를 불러올 수 없습니다. 새로고침해 주세요.
        </p>
      ) : visible.length === 0 ? (
        <p className="mt-5 rounded-2xl border border-line bg-panel px-4 py-12 text-center text-sm text-ink-faint">
          해당하는 예약이 없습니다.
        </p>
      ) : (
        <ul className="mt-5 grid gap-3">
          {visible.map((booking) => (
            <BookingCard
              key={booking.id}
              booking={booking}
              disabled={stale || busyId !== null}
              busy={busyId === booking.id}
              now={now}
              onUpdate={update}
            />
          ))}
        </ul>
      )}
    </>
  );
}

function BookingCard({
  booking,
  disabled,
  busy,
  now,
  onUpdate,
}: {
  booking: AdminBooking;
  disabled: boolean;
  busy: boolean;
  now: number;
  onUpdate: (
    booking: AdminBooking,
    changes: Partial<
      Pick<AdminBooking, "status" | "member_verified" | "host_confirmed" | "parking_confirmed">
    >,
  ) => Promise<void>;
}) {
  const readOnly = booking.status === "declined" || booking.status === "done";
  const ended = Date.parse(booking.end_at) <= now;
  const canApprove =
    !ended &&
    booking.member_verified &&
    (!booking.needs_host || booking.host_confirmed) &&
    (booking.parking === 0 || booking.parking_confirmed);
  const dayCost = Math.max(0, booking.party_size - booking.monthly_pass_count) * 5_000;

  return (
    <li className="rounded-2xl border border-line bg-panel p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-black">{booking.name}</h2>
            <StatusPill status={booking.status} />
          </div>
          <p className="mt-0.5 break-all text-sm text-ink-dim">{booking.contact}</p>
        </div>
        <span className="text-xs text-ink-faint tnum">접수 {formatCreated(booking.created_at)}</span>
      </div>

      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <Info icon={<CalendarClock size={16} />}>
          <strong>{dateFormatter.format(new Date(booking.start_at))}</strong>
          <span className="tnum"> · {formatTimeRange(booking)}</span>
        </Info>
        <Info icon={<Users size={16} />}>
          {booking.party_size}명 · 월 이용권 {booking.monthly_pass_count}명
          {booking.monthly_member_name && ` (${booking.monthly_member_name})`}
        </Info>
        <Info icon={<Car size={16} />}>주차 {booking.parking ? `${booking.parking}대` : "없음"}</Info>
        <Info icon={<Gamepad2 size={16} />}>{booking.games || "게임 미정"}</Info>
      </div>

      <p className="mt-3 rounded-xl bg-panel-2 px-3 py-2 text-sm text-ink-dim">
        예상 1일 이용권 비용 · <strong className="text-ink tnum">{moneyFormatter.format(dayCost)}원</strong>
      </p>

      {booking.note && <p className="mt-3 whitespace-pre-wrap text-sm text-ink-dim">메모 · {booking.note}</p>}

      {booking.needs_night_notice && (
        <p className="mt-3 flex gap-2 rounded-xl border border-weight/30 bg-weight/10 px-3 py-2 text-sm text-weight">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          00:00–09:00 이용은 별도 안내가 필요합니다.
        </p>
      )}

      {!readOnly && (
        <fieldset disabled={disabled} className="mt-4 border-t border-line pt-4 disabled:opacity-60">
          <legend className="mb-2 text-xs font-bold text-ink-faint">이용 조건 확인</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            <Check
              checked={booking.member_verified}
              disabled={booking.status === "approved"}
              onChange={(checked) => void onUpdate(booking, { member_verified: checked })}
              label="월 이용권 소유자 참석 확인"
            />
            {booking.needs_host && (
              <Check
                checked={booking.host_confirmed}
                disabled={booking.status === "approved"}
                onChange={(checked) => void onUpdate(booking, { host_confirmed: checked })}
                label="운영자 동행 확인 (00:10–09:00)"
              />
            )}
            {booking.parking > 0 && (
              <Check
                checked={booking.parking_confirmed}
                disabled={booking.status === "approved"}
                onChange={(checked) => void onUpdate(booking, { parking_confirmed: checked })}
                label={`주차 ${booking.parking}대 확인`}
              />
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {booking.status === "pending" && (
              <button
                type="button"
                disabled={!canApprove || disabled}
                onClick={() => void onUpdate(booking, { status: "approved" })}
                className="rounded-xl bg-accent px-4 py-2 text-sm font-bold text-white transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-40"
              >
                예약 확정
              </button>
            )}
            <button
              type="button"
              disabled={disabled}
              onClick={() => void onUpdate(booking, { status: "declined" })}
              className="rounded-xl border border-line px-4 py-2 text-sm font-bold text-ink-dim transition-colors hover:bg-panel-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40"
            >
              예약 취소
            </button>
            {booking.status === "approved" && ended && (
              <button
                type="button"
                disabled={disabled}
                onClick={() => void onUpdate(booking, { status: "done" })}
                className="rounded-xl border border-rating/40 px-4 py-2 text-sm font-bold text-rating transition-colors hover:bg-rating/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rating disabled:opacity-40"
              >
                이용 완료
              </button>
            )}
            {busy && <span className="self-center text-xs text-ink-faint">저장 중…</span>}
          </div>
        </fieldset>
      )}
    </li>
  );
}

function Info({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-ink-dim">
      <span className="mt-0.5 shrink-0 text-ink-faint">{icon}</span>
      <span>{children}</span>
    </p>
  );
}

function Check({
  checked,
  disabled,
  onChange,
  label,
}: {
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-2 rounded-xl border border-line bg-panel-2 px-3 py-2.5 text-sm text-ink-dim has-checked:border-accent/60 has-checked:text-ink has-disabled:cursor-default">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-4 accent-accent"
      />
      <span>{label}</span>
    </label>
  );
}

function StatusPill({ status }: { status: BookingStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${STATUS_CLASS[status]}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}

function formatTimeRange(booking: AdminBooking) {
  const start = new Date(booking.start_at);
  const end = new Date(booking.end_at);
  const nextDay = dateFormatter.format(start) !== dateFormatter.format(end);
  return `${timeFormatter.format(start)}–${nextDay ? `${dateFormatter.format(end)} ` : ""}${timeFormatter.format(end)}`;
}

function formatCreated(value: string) {
  const date = new Date(value);
  return `${dateFormatter.format(date)} ${timeFormatter.format(date)}`;
}
