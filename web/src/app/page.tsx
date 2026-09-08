import { GameBrowser } from "@/components/GameBrowser";
import { allGameTypes, games, materialCount } from "@/lib/games";
import Link from "next/link";
import { ArrowUpRight, CalendarDays } from "lucide-react";
import { SOCIAL } from "@/lib/site";

export default function Home() {
  const withMaterials = games.filter((g) => materialCount(g) > 0).length;

  return (
    <>
      {SOCIAL && (
        <div className="mx-auto max-w-6xl px-4 pt-5">
          <Link href="/azit" className="flex items-center gap-3 rounded-2xl border border-accent/25 bg-accent/5 px-4 py-4 transition-colors hover:bg-accent/10 sm:px-5">
            <CalendarDays size={24} className="shrink-0 text-accent" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold">보드게임 아지트가 열렸어요</span>
              <span className="mt-1 block text-xs leading-5 text-ink-dim">분당 수내 · 시간표 확인부터 공간 예약까지</span>
            </span>
            <ArrowUpRight size={20} className="shrink-0 text-accent" />
          </Link>
        </div>
      )}
      <section className="border-b border-line bg-panel/40">
        <div className="mx-auto flex max-w-6xl flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-6">
          <h1 className="text-2xl font-black">소장 보드게임</h1>
          <p className="text-sm text-ink-dim tnum">
            {games.length}종 · 자료 있는 게임 {withMaterials}종
          </p>
        </div>
      </section>

      <GameBrowser games={games} gameTypes={allGameTypes()} />
    </>
  );
}
