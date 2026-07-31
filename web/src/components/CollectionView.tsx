"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";

import { type Game } from "@/lib/games";
import { usePlays } from "@/lib/collection";
import { GameCard } from "./GameCard";
import { GameSheet } from "./GameSheet";

export function CollectionView({ games }: { games: Game[] }) {
  const { plays, playedIds, loaded, removePlay, playCount } = usePlays();
  const [showLocked, setShowLocked] = useState(true);
  const [selected, setSelected] = useState<Game | null>(null);

  const byId = useMemo(() => new Map(games.map((g) => [g.id, g])), [games]);

  const unlocked = games.filter((g) => playedIds.has(g.id));
  const locked = games.filter((g) => !playedIds.has(g.id));
  const pct = games.length ? Math.round((unlocked.length / games.length) * 100) : 0;

  if (!loaded) {
    return <div className="mx-auto max-w-6xl px-4 py-16 text-center text-ink-faint">불러오는 중…</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <h1 className="text-2xl font-black">내 카드</h1>
      <p className="mt-1.5 text-sm text-ink-dim">
        플레이를 기록하면 카드가 열립니다. 기록은 이 기기에만 저장됩니다.
      </p>

      {/* --- progress --- */}
      <div className="mt-5 rounded-2xl border border-line bg-panel p-4">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm text-ink-dim">수집률</span>
          <span className="text-sm tnum">
            <strong className="text-xl text-rating">{unlocked.length}</strong>
            <span className="text-ink-faint"> / {games.length} · {pct}%</span>
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-line">
          <div
            className="h-full rounded-full bg-rating transition-[width] duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-ink-faint tnum">
          총 {plays.length}회 플레이 기록
        </p>
      </div>

      {/* --- unlocked cards --- */}
      {unlocked.length === 0 ? (
        <p className="py-12 text-center text-ink-faint">
          아직 기록한 게임이 없습니다.{" "}
          <Link href="/" className="text-accent underline">
            목록에서 게임을 골라
          </Link>{" "}
          첫 카드를 얻어보세요.
        </p>
      ) : (
        <>
          <h2 className="mt-8 mb-3 text-sm font-bold text-ink-dim">
            획득한 카드 {unlocked.length}장
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {unlocked.map((g) => (
              <div key={g.id} className="relative">
                <GameCard game={g} onClick={() => setSelected(g)} />
                <span className="pointer-events-none absolute top-2 left-2 rounded-full bg-rating px-2 py-0.5 text-[10px] font-bold text-black tnum">
                  {playCount(g.id)}회
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* --- play log --- */}
      {plays.length > 0 && (
        <>
          <h2 className="mt-10 mb-3 text-sm font-bold text-ink-dim">플레이 기록</h2>
          <ul className="flex flex-col gap-1.5">
            {plays.map((p, i) => {
              const g = byId.get(p.gameId);
              return (
                <li
                  key={`${p.gameId}-${p.date}-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-line bg-panel px-3.5 py-2.5 text-sm"
                >
                  <span className="w-24 shrink-0 text-ink-faint tnum">{p.date}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {g?.nameKr ?? p.gameId}
                  </span>
                  {p.players != null && (
                    <span className="shrink-0 text-ink-dim tnum">{p.players}인</span>
                  )}
                  {p.note && (
                    <span className="hidden min-w-0 max-w-[40%] truncate text-ink-faint sm:block">
                      {p.note}
                    </span>
                  )}
                  <button
                    onClick={() => removePlay(i)}
                    aria-label="기록 삭제"
                    className="shrink-0 rounded-lg p-1 text-ink-faint transition-colors hover:bg-panel-2 hover:text-weight"
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {/* --- locked --- */}
      {locked.length > 0 && (
        <>
          <div className="mt-10 mb-3 flex items-center gap-3">
            <h2 className="text-sm font-bold text-ink-dim">
              아직 안 해본 게임 {locked.length}종
            </h2>
            <button
              onClick={() => setShowLocked(!showLocked)}
              className="rounded-lg bg-panel px-2.5 py-1 text-xs text-ink-dim transition-colors hover:text-ink"
            >
              {showLocked ? "접기" : "펼치기"}
            </button>
          </div>
          {showLocked && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {locked.map((g) => (
                <GameCard key={g.id} game={g} onClick={() => setSelected(g)} locked />
              ))}
            </div>
          )}
        </>
      )}

      {selected && <GameSheet game={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
