"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, Check, ChevronLeft, ChevronRight, Clock3, Loader2, RefreshCw } from "lucide-react";

import { addDays, blockedIntervals, bookingNightRequirements, kstDate, overlaps, STATUS_CLASS, STATUS_LABEL, toKstIso, validateBooking, type AvailabilityBooking, type BookingInput } from "@/lib/azit";
import { browserSupabase } from "@/lib/supabase-browser";

const fieldClass = "min-w-0 w-full rounded-xl border border-line bg-bg px-3 py-2.5 text-sm text-ink placeholder:text-ink-dim focus:border-accent";
const days = ["월", "화", "수", "목", "금", "토", "일"];
const timeFormat = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const dayFormat = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "long", day: "numeric", weekday: "long" });

type Schedule = { from: string; to: string; bookings: AvailabilityBooking[]; updatedAt: string; error: string | null };

export function AzitBooking({ initialNow }: { initialNow: string }) {
  const [today, setToday] = useState(() => kstDate(new Date(initialNow)));
  const [date, setDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [startTime, setStartTime] = useState("13:00");
  const [endTime, setEndTime] = useState("16:00");
  const [partySize, setPartySize] = useState(4);
  const [monthlyPassCount, setMonthlyPassCount] = useState(1);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [live, setLive] = useState(false);
  const [revision, setRevision] = useState(0);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<AvailabilityBooking | null>(null);
  const [notified, setNotified] = useState(true);

  const monthStart = `${date.slice(0, 7)}-01`;
  const weekday = (new Date(`${monthStart}T12:00:00+09:00`).getUTCDay() + 6) % 7;
  const from = addDays(monthStart, -weekday);
  const to = addDays(from, 42);
  const maxDate = addDays(today, 90);
  const ready = schedule?.from === from && schedule.to === to && !schedule.error;
  const bookings = ready ? schedule.bookings : [];
  const startAt = date && startTime ? toKstIso(date, startTime) : "";
  const endAt = endDate && endTime ? toKstIso(endDate, endTime) : "";
  const duration = Date.parse(endAt) - Date.parse(startAt);
  const validRange = Number.isFinite(duration) && duration > 0 && duration <= 86_400_000;
  const night = validRange ? bookingNightRequirements(startAt, endAt) : { needsNightNotice: false, needsHost: false };
  const active = bookings.filter((b) => b.status === "pending" || b.status === "approved");
  const dailyBookings = active.filter((b) => overlaps(b.start_at, b.end_at, toKstIso(date, "00:00"), toKstIso(addDays(date, 1), "00:00"))).sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at));
  const blocked = blockedIntervals(date);
  const conflict = validRange && active.some((b) => overlaps(startAt, endAt, b.start_at, b.end_at));
  const closed = validRange && [...blocked, ...(endDate !== date ? blockedIntervals(endDate) : [])].some((b) => overlaps(startAt, endAt, b.start_at, b.end_at));
  const cost = Math.max(0, partySize - monthlyPassCount) * 5000;
  const currentReceipt = receipt ? bookings.find((b) => b.id === receipt.id) ?? receipt : null;

  useEffect(() => {
    let cancelled = false;
    let fetching = false;
    const controller = new AbortController();
    async function refresh() {
      if (fetching || cancelled) return;
      fetching = true;
      try {
        const response = await fetch(`/api/azit?from=${from}&to=${to}`, { cache: "no-store", signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "시간표를 불러오지 못했어요.");
        if (!cancelled) {
          setSchedule({ from, to, bookings: data.bookings, updatedAt: data.updatedAt, error: null });
          setToday(kstDate(new Date()));
        }
      } catch (err) {
        if (!cancelled) setSchedule((prev) => ({ from, to, bookings: prev?.from === from ? prev.bookings : [], updatedAt: prev?.updatedAt ?? "", error: err instanceof Error ? err.message : "시간표를 불러오지 못했어요." }));
      } finally {
        fetching = false;
      }
    }
    void refresh();
    const interval = window.setInterval(() => { if (!document.hidden) void refresh(); }, 15_000);
    const onVisible = () => { if (!document.hidden) void refresh(); };
    window.addEventListener("focus", onVisible);
    window.addEventListener("online", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    let disconnect: (() => void) | undefined;
    try {
      const supabase = browserSupabase();
      const channel = supabase.channel("azit-availability")
        .on("broadcast", { event: "booking_changed" }, () => { void refresh(); })
        .subscribe((status) => { if (!cancelled) setLive(status === "SUBSCRIBED"); });
      disconnect = () => { void supabase.removeChannel(channel); };
    } catch {
      // The public schedule still refreshes when the optional browser key is absent.
    }
    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(interval);
      window.removeEventListener("focus", onVisible);
      window.removeEventListener("online", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
      disconnect?.();
    };
  }, [from, to, revision]);

  function selectDate(value: string) {
    if (!value || value < today || value > maxDate) return;
    setDate(value);
    setEndDate(value);
    setError(null);
  }

  function moveMonth(offset: number) {
    const next = new Date(`${monthStart}T12:00:00+09:00`);
    next.setUTCMonth(next.getUTCMonth() + offset);
    selectDate(kstDate(next) < today ? today : kstDate(next));
  }

  function selectTime(hour: number) {
    setStartTime(`${String(hour).padStart(2, "0")}:00`);
    setEndTime(`${String((hour + 1) % 24).padStart(2, "0")}:00`);
    setEndDate(hour === 23 ? addDays(date, 1) : date);
    setError(null);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending || !ready) return;
    setError(null);
    const fields = new FormData(event.currentTarget);
    const input: BookingInput = {
      startAt, endAt, partySize, monthlyPassCount,
      name: String(fields.get("name") ?? ""),
      contact: String(fields.get("contact") ?? "").trim() ? `${fields.get("channel")} ${String(fields.get("contact")).trim()}` : "",
      monthlyMemberName: String(fields.get("monthlyMemberName") ?? ""),
      parking: Number(fields.get("parking")),
      games: String(fields.get("games") ?? ""),
      note: String(fields.get("note") ?? ""),
      rulesAccepted: fields.get("rulesAccepted") === "on",
      nightNoticeAccepted: fields.get("nightNoticeAccepted") === "on",
      hostPresenceRequested: fields.get("hostPresenceRequested") === "on",
      website: String(fields.get("website") ?? ""),
    };
    const validation = validateBooking(input);
    if (validation.error) { setError(validation.error); return; }
    if (conflict || closed) { setError("선택한 시간에 이용할 수 없는 구간이 있어요. 시간표를 다시 확인해 주세요."); return; }
    setSending(true);
    try {
      const response = await fetch("/api/azit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "신청을 접수하지 못했어요.");
      setReceipt(data.booking);
      setNotified(data.notified === true);
      setRevision((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "신청을 접수하지 못했어요.");
      setRevision((n) => n + 1);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div><p className="text-xs font-bold text-accent">시간이 맞으면, 모여요</p><h2 className="mt-2 text-2xl font-black">시간표 & 공간 예약</h2></div>
        <p className="flex items-center gap-1.5 text-xs text-ink-dim"><Clock3 size={13} /> 모든 시간은 한국 시간 기준</p>
      </div>
      <div className="grid items-start gap-5 lg:grid-cols-[1.15fr_1fr]">
        <section aria-label="이용 가능 시간표" className="min-w-0 rounded-2xl border border-line bg-panel p-4 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h3 className="flex items-center gap-2 font-bold"><CalendarDays size={19} className="text-accent" /> {Number(date.slice(0, 4))}년 {Number(date.slice(5, 7))}월</h3>
            <div className="flex items-center gap-1">
              <button type="button" onClick={() => selectDate(today)} className="rounded-lg px-3 py-2 text-xs text-ink-dim hover:bg-panel-2">오늘</button>
              <button type="button" onClick={() => moveMonth(-1)} disabled={date.slice(0, 7) <= today.slice(0, 7)} aria-label="이전 달" className="rounded-lg p-2 hover:bg-panel-2 disabled:opacity-30"><ChevronLeft size={18} /></button>
              <button type="button" onClick={() => moveMonth(1)} disabled={date.slice(0, 7) >= maxDate.slice(0, 7)} aria-label="다음 달" className="rounded-lg p-2 hover:bg-panel-2 disabled:opacity-30"><ChevronRight size={18} /></button>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            {days.map((day) => <span key={day} className="pb-2 text-xs text-ink-dim">{day}</span>)}
            {Array.from({ length: 42 }, (_, i) => {
              const value = addDays(from, i);
              const dayBookings = active.filter((b) => overlaps(b.start_at, b.end_at, toKstIso(value, "00:00"), toKstIso(addDays(value, 1), "00:00")));
              const unavailable = value < today || value > maxDate;
              return <button key={value} type="button" disabled={unavailable} aria-pressed={date === value} aria-label={`${dayFormat.format(new Date(toKstIso(value, "12:00")))}${dayBookings.length ? `, 예약 ${dayBookings.length}건` : ""}`} onClick={() => selectDate(value)} className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl text-sm transition-colors disabled:opacity-25 sm:min-h-14 ${date === value ? "bg-accent font-bold text-bg" : value.slice(0, 7) !== date.slice(0, 7) ? "text-ink-dim hover:bg-panel-2" : "hover:bg-panel-2"}`}>
                <span className={value === today && date !== value ? "font-bold text-accent" : ""}>{Number(value.slice(-2))}</span>
                <span className="flex h-1 gap-1" aria-hidden>{dayBookings.some((b) => b.status === "pending") && <span className={`size-1 rounded-full ${date === value ? "bg-bg" : "bg-weight"}`} />}{dayBookings.some((b) => b.status === "approved") && <span className={`size-1 rounded-full ${date === value ? "bg-bg" : "bg-accent"}`} />}</span>
              </button>;
            })}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4">
            <p className="text-sm font-bold">{dayFormat.format(new Date(toKstIso(date, "12:00")))}</p>
            <button type="button" onClick={() => setRevision((n) => n + 1)} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-ink-dim hover:bg-panel-2"><RefreshCw size={12} /> 새로고침</button>
          </div>
          <div aria-live="polite" className="mt-2 text-xs leading-5 text-ink-dim">
            {schedule?.from === from && schedule.error ? <p role="alert" className="rounded-xl border border-weight/30 bg-weight/10 p-3 text-weight">{schedule.error} 최신 시간표를 확인한 뒤 신청할 수 있어요.</p> : ready ? <p><span className="mr-1.5 inline-block size-1.5 rounded-full bg-accent" aria-hidden />{live ? "실시간 연결" : "15초마다 자동 갱신"} · {timeFormat.format(new Date(schedule.updatedAt))} 갱신</p> : <p className="flex items-center gap-2"><Loader2 size={13} className="animate-spin motion-reduce:animate-none" /> 시간표를 불러오고 있어요…</p>}
          </div>

          <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-ink-dim">
            <span>○ 신청 가능</span><span className="text-weight">● 예약 접수중</span><span className="text-accent">● 예약 확정</span><span>— 이용 불가</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-ink-dim">시작 시간을 누르고 예약 신청서에서 종료 시간을 조정해 주세요. 심야 시간도 동행 확인 후 이용할 수 있어요.</p>
          <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-6">
            {Array.from({ length: 24 }, (_, hour) => {
              const start = toKstIso(date, `${String(hour).padStart(2, "0")}:00`);
              const end = hour === 23 ? toKstIso(addDays(date, 1), "00:00") : toKstIso(date, `${String(hour + 1).padStart(2, "0")}:00`);
              const fixed = blocked.some((b) => overlaps(start, end, b.start_at, b.end_at));
              const booked = active.find((b) => overlaps(start, end, b.start_at, b.end_at));
              const past = Date.parse(start) <= Date.parse(schedule?.updatedAt || initialNow);
              const unavailable = !ready || fixed || Boolean(booked) || past;
              const label = !ready ? "확인 중" : past ? "지난 시간" : fixed ? "이용 불가" : booked ? STATUS_LABEL[booked.status] : hour < 9 ? "심야 협의" : "신청 가능";
              return <button key={hour} type="button" disabled={unavailable} onClick={() => selectTime(hour)} aria-pressed={!unavailable && startTime === `${String(hour).padStart(2, "0")}:00`} aria-label={`${String(hour).padStart(2, "0")}:00부터 1시간, ${label}`} className={`rounded-xl border px-1 py-2.5 text-center transition-colors ${booked && !past ? `${STATUS_CLASS[booked.status]} border-transparent` : unavailable ? "border-transparent bg-bg/50 text-ink-dim" : startTime === `${String(hour).padStart(2, "0")}:00` ? "border-accent bg-accent/10 text-accent" : "border-line bg-bg hover:border-accent"}`}>
                <span className="block text-xs font-bold tnum">{String(hour).padStart(2, "0")}:00</span><span className="mt-1 block text-[10px]">{label}</span>
              </button>;
            })}
          </div>
          <p className="mt-2 text-[11px] leading-5 text-ink-dim">시간 버튼은 1시간 단위예요. 일부만 예약된 시간의 남은 구간은 신청서에서 10분 단위로 선택할 수 있어요.</p>
          <div className="mt-4 space-y-2 rounded-xl bg-bg p-3 text-xs">
            {blocked.map((b) => <p key={b.start_at} className="flex justify-between gap-3 text-ink-dim"><span>{timeFormat.format(new Date(b.start_at))}–{timeFormat.format(new Date(b.end_at))}</span><span>정기 이용 불가</span></p>)}
            {ready && dailyBookings.map((b) => <p key={b.id} className="flex flex-wrap justify-between gap-2"><span className="tnum">{kstDate(new Date(b.start_at)) < date ? "전날부터" : timeFormat.format(new Date(b.start_at))}–{kstDate(new Date(b.end_at)) > date ? "다음날까지" : timeFormat.format(new Date(b.end_at))}</span><span className={b.status === "pending" ? "text-weight" : "text-accent"}>{STATUS_LABEL[b.status]}</span></p>)}
            {ready && dailyBookings.length === 0 && <p className="text-ink-dim">이 날짜에 접수중이거나 확정된 예약이 없어요.</p>}
          </div>
          <p className="mt-3 text-xs leading-5 text-ink-dim">접수중인 시간은 운영자 확인 전까지 다른 신청을 받지 않아요.</p>
        </section>

        <section aria-label="공간 예약 신청" className="min-w-0 rounded-2xl border border-line bg-panel p-4 sm:p-6">
          {currentReceipt ? (
            <div role="status" className="py-5 text-center">
              <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-accent/15 text-accent"><Check size={28} /></span>
              <h3 className="mt-4 text-xl font-black">예약 신청이 접수됐어요</h3>
              <p className="mt-3"><span className={`rounded-full px-3 py-1 text-sm font-bold ${STATUS_CLASS[currentReceipt.status]}`}>{STATUS_LABEL[currentReceipt.status]}</span></p>
              <p className="mt-4 text-sm leading-7 text-ink-dim">{dayFormat.format(new Date(currentReceipt.start_at))}<br />{timeFormat.format(new Date(currentReceipt.start_at))} → {kstDate(new Date(currentReceipt.start_at)) !== kstDate(new Date(currentReceipt.end_at)) ? "다음날 " : ""}{timeFormat.format(new Date(currentReceipt.end_at))}</p>
              <p className="mt-4 text-sm leading-7 text-ink-dim">운영자가 월 이용권과 이용 조건을 확인한 뒤 연락드려요. <strong className="text-ink">‘예약 확정’ 안내를 받은 후 이용해 주세요.</strong></p>
              <p className="mt-3 text-xs text-ink-dim">예약 번호 · {currentReceipt.id.slice(0, 8)}</p>
              <p className="mt-2 text-xs leading-5 text-ink-dim">변경·취소가 필요하면 예약 번호와 함께 운영자에게 연락해 주세요.</p>
              {!notified && <p className="mt-4 rounded-xl bg-weight/10 p-3 text-sm leading-6 text-weight">예약은 접수됐지만 운영자 알림이 전달되지 않았어요. 예약 번호와 함께 운영자에게 직접 알려주세요.</p>}
              <button type="button" onClick={() => { setReceipt(null); setError(null); }} className="mt-6 rounded-xl border border-line px-4 py-3 text-sm hover:bg-panel-2">다른 일정 신청하기</button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-5">
              <div><h3 className="text-lg font-black">공간 예약 신청</h3><p className="mt-1 text-xs leading-5 text-ink-dim">신청 즉시 접수중으로 표시돼요. 운영자 확인 후 확정됩니다.</p></div>
              <fieldset disabled={sending} className="min-w-0 space-y-4 disabled:opacity-60">
                <legend className="sr-only">예약 정보</legend>
                <div className="grid min-w-0 grid-cols-2 gap-3">
                  <label className="min-w-0 space-y-1.5 text-xs text-ink-dim"><span>이용 시작일</span><input aria-label="이용 시작일" type="date" required min={today} max={maxDate} value={date} onChange={(e) => selectDate(e.target.value)} className={fieldClass} /></label>
                  <label className="min-w-0 space-y-1.5 text-xs text-ink-dim"><span>시작 시간</span><input aria-label="시작 시간" type="time" required step={600} value={startTime} onChange={(e) => setStartTime(e.target.value)} className={fieldClass} /></label>
                  <label className="min-w-0 space-y-1.5 text-xs text-ink-dim"><span>이용 종료일</span><input aria-label="이용 종료일" type="date" required min={date} max={addDays(date, 1)} value={endDate} onChange={(e) => setEndDate(e.target.value)} className={fieldClass} /></label>
                  <label className="min-w-0 space-y-1.5 text-xs text-ink-dim"><span>종료 시간</span><input aria-label="종료 시간" type="time" required step={600} value={endTime} onChange={(e) => setEndTime(e.target.value)} className={fieldClass} /></label>
                </div>
                <p className="text-xs leading-5 text-ink-dim">자정을 넘기면 종료일을 다음 날로 선택해 주세요. 한 번에 최대 24시간, 90일 이내 일정을 신청할 수 있어요.</p>
                {!validRange && <p role="alert" className="rounded-xl bg-weight/10 p-3 text-xs leading-5 text-weight">종료일시는 시작일시 이후, 24시간 이내로 선택해 주세요.</p>}
                {(closed || conflict) && <p role="alert" className="rounded-xl bg-weight/10 p-3 text-xs leading-5 text-weight">{closed ? "정기 이용 불가 시간이 포함되어 있어요." : "이미 접수중이거나 확정된 예약과 시간이 겹쳐요."} 다른 시간을 선택해 주세요.</p>}
                <div className="grid grid-cols-2 gap-3">
                  <label className="space-y-1.5 text-xs text-ink-dim"><span>전체 인원</span><input name="partySize" type="number" required min={1} max={50} value={partySize} onChange={(e) => setPartySize(Number(e.target.value))} className={fieldClass} /></label>
                  <label className="space-y-1.5 text-xs text-ink-dim"><span>월 이용권 보유 인원</span><input name="monthlyPassCount" type="number" required min={1} max={partySize || 1} value={monthlyPassCount} onChange={(e) => setMonthlyPassCount(Number(e.target.value))} className={fieldClass} /></label>
                </div>
                <label className="block space-y-1.5 text-xs text-ink-dim"><span>동행하는 월 이용권 보유자 이름 / 닉네임 <span className="text-weight">*</span></span><input name="monthlyMemberName" required maxLength={80} placeholder="운영자가 이용권을 확인할 수 있는 이름" className={fieldClass} /></label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="space-y-1.5 text-xs text-ink-dim"><span>신청자 이름 <span className="text-weight">*</span></span><input name="name" required autoComplete="name" maxLength={80} placeholder="이름 또는 닉네임" className={fieldClass} /></label>
                  <label className="space-y-1.5 text-xs text-ink-dim"><span>연락 방법</span><select name="channel" className={fieldClass}><option>당근</option><option>카카오톡</option><option>전화</option></select></label>
                </div>
                <label className="block space-y-1.5 text-xs text-ink-dim"><span>연락처 <span className="text-weight">*</span></span><input name="contact" required maxLength={180} placeholder="당근 닉네임 · 카톡 ID · 전화번호" className={fieldClass} /></label>
                <label className="block space-y-1.5 text-xs text-ink-dim"><span>주차 요청</span><select name="parking" className={fieldClass}><option value="0">주차하지 않아요</option><option value="1">1대 · 사전 확인 필요</option><option value="2">2대 · 사전 확인 필요</option></select></label>
                <label className="block space-y-1.5 text-xs text-ink-dim"><span className="flex flex-wrap justify-between gap-1">하고 싶은 보드게임 (선택)<Link href="/" target="_blank" className="text-accent hover:underline">게임 목록 ↗</Link></span><input name="games" maxLength={500} placeholder="예) 아크 노바, 브라스 버밍엄" className={fieldClass} /></label>
                <label className="block space-y-1.5 text-xs text-ink-dim"><span>요청 사항 (선택)</span><textarea name="note" rows={2} maxLength={1000} placeholder="주차·이용권 문의 등 운영자에게 알려주세요" className={fieldClass} /></label>
                <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="absolute -left-[9999px] size-0" />
                {night.needsNightNotice && <div className="space-y-3 rounded-xl border border-weight/30 bg-weight/5 p-3 text-xs leading-6">
                  <p className="font-bold text-weight">심야 이용 · 별도 안내가 필요해요</p>
                  <label className="flex items-start gap-2"><input type="checkbox" name="nightNoticeAccepted" required className="mt-1 size-4 shrink-0 accent-accent" /><span>자정 이후 이용과 상가 출입 안내를 운영자에게 확인하겠습니다.</span></label>
                  {night.needsHost && <label className="flex items-start gap-2"><input type="checkbox" name="hostPresenceRequested" required className="mt-1 size-4 shrink-0 accent-accent" /><span>00:10–09:00에는 운영자 동행이 필요함을 이해하고, 동행 가능 여부 확인을 요청합니다.</span></label>}
                </div>}
                <label className="flex items-start gap-2 text-xs leading-6 text-ink-dim"><input type="checkbox" name="rulesAccepted" required className="mt-1 size-4 shrink-0 accent-accent" /><span>월 이용권 보유자 1명 이상이 동행하며, 이용 후 뒷정리·분리수거·보드게임 구성품 정리를 하겠습니다. 신청만으로 예약이 확정되지 않음을 확인했습니다.</span></label>
              </fieldset>
              <div className="rounded-xl bg-bg p-4">
                <p className="flex flex-wrap items-center justify-between gap-2 text-sm"><span className="text-ink-dim">1일 이용권 예상 금액</span><strong className="text-xl tnum">{cost.toLocaleString("ko-KR")}원</strong></p>
                <p className="mt-1 text-xs leading-5 text-ink-dim">{Math.max(0, partySize - monthlyPassCount)}명 × 5,000원 · 기존 월 이용권 보유 {monthlyPassCount}명 제외</p>
                <p className="mt-2 text-xs leading-5 text-ink-dim">월 이용권은 1인 15,000원입니다. 이용권 구매·최종 금액·결제 방법은 운영자에게 확인해 주세요.</p>
              </div>
              {error && <p role="alert" className="rounded-xl bg-weight/10 p-3 text-sm text-weight">{error}</p>}
              <button type="submit" disabled={sending || !ready || closed || conflict || !validRange} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3.5 font-bold text-bg hover:opacity-90 disabled:opacity-40">{sending ? <Loader2 size={17} className="animate-spin motion-reduce:animate-none" /> : <ArrowRight size={17} />}{sending ? "예약 접수 중…" : "예약 신청하기"}</button>
              <p className="text-center text-[11px] leading-5 text-ink-dim">{!ready ? "최신 시간표를 불러온 뒤 신청할 수 있어요." : "온라인 결제 없이 신청만 접수합니다. 연락처는 운영자만 확인해요."}</p>
            </form>
          )}
        </section>
      </div>
    </>
  );
}
