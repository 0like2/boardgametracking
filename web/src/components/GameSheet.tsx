"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  CalendarPlus,
  ChevronRight,
  Clock,
  FileText,
  Info,
  PackageOpen,
  Sparkles,
  Users,
} from "lucide-react";

import {
  type Game,
  bestPlayersText,
  coverSrc,
  materialCount,
  playersText,
  timeText,
} from "@/lib/games";
import { usePlays } from "@/lib/collection";
import { PlayLogger } from "./PlayLogger";
import { RequestForm } from "./RequestForm";
import { Sheet } from "./Sheet";

type Mode = "menu" | "rental" | "meetup" | "play";

export function GameSheet({ game, onClose }: { game: Game; onClose: () => void }) {
  const [mode, setMode] = useState<Mode>("menu");
  const { playCount, loaded } = usePlays();
  const count = playCount(game.id);

  const titles: Record<Mode, string> = {
    menu: game.nameKr,
    rental: `${game.nameKr} 대여 예약`,
    meetup: `${game.nameKr} 모임 열어주세요`,
    play: `${game.nameKr} 플레이 기록`,
  };

  return (
    <Sheet
      title={titles[mode]}
      onClose={onClose}
      onBack={mode === "menu" ? undefined : () => setMode("menu")}
    >
      {mode === "menu" && (
        <div className="flex flex-col gap-5">
          {/* --- art + blurb --- */}
          <div className="relative aspect-video w-full overflow-hidden rounded-2xl">
            <Image
              src={coverSrc(game)}
              alt={game.nameKr}
              fill
              sizes="(max-width: 640px) 100vw, 480px"
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 p-4">
              <p className="text-xs text-rating">{game.nameEn}</p>
              {game.summary && (
                <p className="mt-1 line-clamp-3 text-sm leading-snug text-ink">
                  {game.summary}
                </p>
              )}
            </div>
          </div>

          {/* --- quick stats --- */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <QuickStat
              icon={<Users size={16} />}
              value={playersText(game)}
              sub={bestPlayersText(game) ? `추천 ${bestPlayersText(game)}` : "—"}
            />
            <QuickStat
              icon={<Clock size={16} />}
              value={timeText(game)}
              sub={game.minAge != null ? `${game.minAge}세 이상` : "—"}
            />
            <QuickStat
              icon={<Info size={16} />}
              value={game.weight != null ? game.weight.toFixed(1) : "—"}
              sub="난이도"
            />
          </div>

          {/* --- actions --- */}
          <div className="flex flex-col gap-2">
            <ActionButton
              onClick={() => setMode("rental")}
              icon={<PackageOpen size={18} />}
              label="대여 예약"
              hint="이 게임을 빌리고 싶어요"
              tone="weight"
            />
            <ActionButton
              onClick={() => setMode("meetup")}
              icon={<CalendarPlus size={18} />}
              label="모임 열어주세요"
              hint="이 게임 하고 싶어요 — 당근모임으로 열어주세요"
              tone="accent"
            />
            <ActionButton
              onClick={() => setMode("play")}
              icon={<Sparkles size={18} />}
              label={loaded && count > 0 ? `플레이 기록 (${count}회)` : "플레이 기록"}
              hint="기록하면 카드를 획득합니다"
            />
            {materialCount(game) > 0 && (
              <Link
                href={`/game/${game.slug}`}
                className="flex items-center gap-3 rounded-xl border border-line bg-panel px-4 py-3 transition-colors hover:bg-panel-2"
              >
                <span className="text-ink-faint">
                  <FileText size={18} />
                </span>
                <span className="min-w-0 flex-1 text-left">
                  <span className="block font-bold">자료 {materialCount(game)}개</span>
                  <span className="block text-xs text-ink-faint">
                    {[...new Set([...game.materials, ...game.boardlifeFiles].map((m) => m.kind))].join(" · ")}
                  </span>
                </span>
                <ChevronRight size={16} className="shrink-0 text-ink-faint" />
              </Link>
            )}
            <Link
              href={`/game/${game.slug}`}
              className="flex items-center gap-3 rounded-xl border border-line bg-panel px-4 py-3 transition-colors hover:bg-panel-2"
            >
              <span className="text-ink-faint">
                <Info size={18} />
              </span>
              <span className="min-w-0 flex-1 text-left font-bold">상세 정보</span>
              <ChevronRight size={16} className="shrink-0 text-ink-faint" />
            </Link>
          </div>
        </div>
      )}

      {mode === "rental" && (
        <RequestForm
          type="rental"
          hidden={{ gameName: game.nameKr, gameSlug: game.slug }}
          submitLabel="대여 예약 보내기"
          successText="확인 후 연락드릴게요."
          fields={[
            { name: "pickupDate", label: "대여 희망일", type: "date", half: true },
            { name: "returnDate", label: "반납 예정일", type: "date", half: true },
            {
              name: "note",
              label: "메모",
              type: "textarea",
              placeholder: "수령 방법, 함께 빌리고 싶은 게임 등",
            },
          ]}
        />
      )}

      {mode === "meetup" && (
        <>
          <p className="mb-4 rounded-xl bg-panel px-3.5 py-2.5 text-xs leading-relaxed text-ink-dim">
            <strong className="text-ink">{game.nameKr}</strong> 모임을 열어달라는
            요청이 전달됩니다. 인원이 모이면 당근모임에 올리고 연락드릴게요.
            {bestPlayersText(game) && ` (베스트 ${bestPlayersText(game)})`}
          </p>
          <RequestForm
            type="meetup"
            hidden={{ games: game.nameKr, gameSlug: game.slug }}
            submitLabel="모임 열어달라고 요청하기"
            successText="인원이 모이면 당근모임에 올리고 연락드릴게요."
            fields={[{ name: "days", label: "가능한 요일", type: "days" }]}
          />
        </>
      )}

      {mode === "play" && <PlayLogger game={game} onDone={onClose} />}
    </Sheet>
  );
}

function QuickStat({
  icon,
  value,
  sub,
}: {
  icon: React.ReactNode;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-xl bg-panel px-2 py-2.5">
      <span className="flex justify-center text-ink-faint">{icon}</span>
      <p className="mt-1 font-bold tnum">{value}</p>
      <p className="text-[11px] text-ink-faint">{sub}</p>
    </div>
  );
}

function ActionButton({
  onClick,
  icon,
  label,
  hint,
  tone,
}: {
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  hint: string;
  tone?: "weight" | "accent";
}) {
  const toneClass =
    tone === "weight"
      ? "bg-weight text-black hover:opacity-90"
      : tone === "accent"
        ? "bg-accent text-white hover:opacity-90"
        : "border border-line bg-panel text-ink hover:bg-panel-2";

  const hintClass = tone ? "opacity-75" : "text-ink-faint";

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 rounded-xl px-4 py-3 transition-colors ${toneClass}`}
    >
      <span>{icon}</span>
      <span className="min-w-0 flex-1 text-left">
        <span className="block font-bold">{label}</span>
        <span className={`block text-xs ${hintClass}`}>{hint}</span>
      </span>
      <ChevronRight size={16} className="shrink-0 opacity-60" />
    </button>
  );
}
