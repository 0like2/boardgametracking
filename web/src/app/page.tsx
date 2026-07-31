import { GameBrowser } from "@/components/GameBrowser";
import { allGameTypes, games, materialCount } from "@/lib/games";

export default function Home() {
  const withMaterials = games.filter((g) => materialCount(g) > 0).length;

  return (
    <>
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
