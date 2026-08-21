import { notFound } from "next/navigation";

import { SOCIAL } from "@/lib/site";
import type { Metadata } from "next";
import Link from "next/link";
import { CalendarPlus, PackageOpen } from "lucide-react";

import { serverSupabase } from "@/lib/supabase";

export const metadata: Metadata = {
  title: "신청 현황 · 보드게임 컬렉션",
  description: "최근 대여 예약과 모임 신청 현황.",
};

// Always show the latest; this page is a live status board.
export const dynamic = "force-dynamic";

type Row = {
  id: string;
  type: "rental" | "meetup";
  name: string;
  status: string;
  created_at: string;
  payload: Record<string, string>;
};

const STATUS_LABEL: Record<string, string> = {
  pending: "확인 중",
  approved: "확정",
  declined: "취소",
  done: "완료",
};

const STATUS_CLASS: Record<string, string> = {
  pending: "bg-panel-2 text-ink-dim",
  approved: "bg-accent/15 text-accent",
  declined: "bg-line text-ink-faint line-through",
  done: "bg-rating/15 text-rating",
};

/** 홍길동 -> 홍*동, 김철 -> 김*  — enough to recognise yourself, not others. */
function maskName(name: string): string {
  if (name.length <= 1) return name;
  if (name.length === 2) return `${name[0]}*`;
  return `${name[0]}${"*".repeat(name.length - 2)}${name.at(-1)}`;
}

export default async function RequestsPage() {
  if (!SOCIAL) notFound();

  const supabase = serverSupabase();

  let rows: Row[] = [];
  let error: string | null = null;

  if (!supabase) {
    error =
      "Supabase가 아직 연결되지 않았습니다. 신청은 디스코드와 이메일로는 정상 전달됩니다.";
  } else {
    const { data, error: dbError } = await supabase
      .from("requests")
      .select("id, type, name, status, created_at, payload")
      .order("created_at", { ascending: false })
      .limit(50);

    if (dbError) error = `현황을 불러오지 못했습니다: ${dbError.message}`;
    else rows = (data ?? []) as Row[];
  }

  // Group open meetup requests by game so the board shows what has traction.
  const byGame = new Map<string, Row[]>();
  for (const r of rows) {
    if (r.type !== "meetup" || r.status !== "pending") continue;
    const key = r.payload.games?.trim() || "게임 미지정";
    byGame.set(key, [...(byGame.get(key) ?? []), r]);
  }
  const demand = [...byGame.entries()].sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-2xl font-black">신청 현황</h1>
        <Link
          href="/meetup"
          className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-2 text-sm font-bold text-white transition-opacity hover:opacity-90"
        >
          <CalendarPlus size={16} /> 모임 열어주세요
        </Link>
      </div>
      <p className="mt-1.5 text-sm text-ink-dim">
        최근 대여 예약과 모임 요청입니다. 게임 카드를 눌러도 신청할 수 있어요.
      </p>

      {error && (
        <p className="mt-5 rounded-xl border border-line bg-panel px-4 py-3 text-sm text-ink-dim">
          {error}
        </p>
      )}

      {demand.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-1 text-sm font-bold text-ink-dim">모임 대기 중인 게임</h2>
          <p className="mb-2 text-xs text-ink-faint">
            요청이 많은 순입니다. 인원이 모이면 당근모임에 올립니다.
          </p>
          <div className="flex flex-col gap-2">
            {demand.map(([gameName, reqs]) => (
              <div
                key={gameName}
                className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="font-bold">🎲 {gameName}</span>
                  <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-bold text-white tnum">
                    {reqs.length}명 대기
                  </span>
                </div>
                <p className="mt-1 text-xs text-ink-dim">
                  가능한 요일 · {summariseDays(reqs)}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-6">
        <h2 className="mb-2 text-sm font-bold text-ink-dim">전체 내역</h2>
        {rows.length === 0 ? (
          <p className="rounded-xl border border-line bg-panel px-4 py-8 text-center text-sm text-ink-faint">
            아직 신청 내역이 없습니다.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {rows.map((r) => (
              <li
                key={r.id}
                className="flex items-start gap-3 rounded-xl border border-line bg-panel px-4 py-3"
              >
                <span
                  className={`mt-0.5 shrink-0 ${
                    r.type === "rental" ? "text-weight" : "text-accent"
                  }`}
                >
                  {r.type === "rental" ? <PackageOpen size={18} /> : <CalendarPlus size={18} />}
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <span className="font-bold">
                      {r.type === "rental"
                        ? r.payload.gameName || "게임 대여"
                        : `${r.payload.games || "게임 미지정"} 모임`}
                    </span>
                    <StatusPill status={r.status} />
                  </div>
                  <p className="mt-0.5 text-xs text-ink-faint">
                    {maskName(r.name)} ·{" "}
                    {r.type === "rental"
                      ? `${r.payload.pickupDate || "날짜 미정"} ~ ${r.payload.returnDate || "미정"}`
                      : r.payload.days
                        ? `${r.payload.days.split(",").join("·")}요일 가능`
                        : "아무 때나"}
                  </p>
                </div>

                <span className="shrink-0 text-xs text-ink-faint tnum">
                  {r.created_at.slice(5, 10)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
        STATUS_CLASS[status] ?? STATUS_CLASS.pending
      }`}
    >
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

const DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"];

/**
 * "토 3명 · 일 2명" — where the requesters actually overlap, which is the
 * thing you need to know before picking a date.
 */
function summariseDays(rows: Row[]): string {
  const counts = new Map<string, number>();
  let anyDay = 0;

  for (const r of rows) {
    const days = (r.payload.days ?? "").split(",").filter(Boolean);
    if (days.length === 0) anyDay += 1;
    for (const d of days) counts.set(d, (counts.get(d) ?? 0) + 1);
  }

  const parts = DAY_ORDER.filter((d) => counts.has(d)).map(
    (d) => `${d} ${counts.get(d)}명`,
  );
  if (anyDay > 0) parts.push(`아무 때나 ${anyDay}명`);
  return parts.join(" · ") || "미정";
}
