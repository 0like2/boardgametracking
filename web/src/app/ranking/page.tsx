import { notFound } from "next/navigation";

import { SOCIAL } from "@/lib/site";
import type { Metadata } from "next";
import { Lock, Trophy } from "lucide-react";

import { AuthButton } from "@/components/AuthButton";
import { currentUser, userSupabase } from "@/lib/supabase-server";

export const metadata: Metadata = {
  title: "랭킹보드 · 보드게임 컬렉션",
  description: "플레이 기록으로 집계한 전적.",
};

export const dynamic = "force-dynamic";

type Standing = {
  player_name: string;
  games_played: number;
  wins: number;
  win_rate: number | null;
  avg_rank: number | null;
  last_played: string | null;
};

type RecentPlay = {
  id: string;
  game_name: string;
  played_on: string;
  play_results: { player_name: string; rank: number; score: number | null }[];
};

export default async function RankingPage() {
  if (!SOCIAL) notFound();

  const user = await currentUser();

  if (!user) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-24 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-panel text-ink-faint">
          <Lock size={26} />
        </span>
        <h1 className="text-xl font-black">랭킹보드는 로그인이 필요합니다</h1>
        <p className="text-sm leading-relaxed text-ink-dim">
          누가 몇 번 이겼는지는 같이 플레이한 사람들만 봅니다. 구글 계정으로
          로그인해 주세요.
        </p>
        <AuthButton next="/ranking" />
      </div>
    );
  }

  const supabase = await userSupabase();
  const [{ data: standings }, { data: recent }] = await Promise.all([
    supabase!
      .from("player_standings")
      .select("*")
      .order("wins", { ascending: false })
      .limit(50),
    supabase!
      .from("plays")
      .select("id, game_name, played_on, play_results(player_name, rank, score)")
      .order("played_on", { ascending: false })
      .limit(10),
  ]);

  const rows = (standings ?? []) as Standing[];
  const plays = (recent ?? []) as RecentPlay[];

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-black">랭킹보드</h1>
      <p className="mt-1.5 mb-6 text-sm text-ink-dim">
        기록된 판을 집계한 전적입니다. {user.name}님 안녕하세요.
      </p>

      {rows.length === 0 ? (
        <p className="rounded-xl border border-line bg-panel px-4 py-10 text-center text-sm text-ink-faint">
          아직 기록된 판이 없습니다. 게임 카드에서 플레이를 기록하면 여기에 쌓입니다.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-line">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr className="bg-panel-2 text-left text-xs text-ink-faint">
                <th className="px-4 py-3 font-medium">순위</th>
                <th className="px-4 py-3 font-medium">이름</th>
                <th className="px-4 py-3 text-right font-medium">판수</th>
                <th className="px-4 py-3 text-right font-medium">승</th>
                <th className="px-4 py-3 text-right font-medium">승률</th>
                <th className="px-4 py-3 text-right font-medium">평균 등수</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.player_name} className="border-t border-line bg-panel">
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex size-7 items-center justify-center rounded-full text-xs font-black ${
                        i === 0
                          ? "bg-rating text-black"
                          : i === 1
                            ? "bg-ink-dim text-black"
                            : i === 2
                              ? "bg-weight/70 text-black"
                              : "bg-panel-2 text-ink-faint"
                      }`}
                    >
                      {i + 1}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-bold">{r.player_name}</td>
                  <td className="px-4 py-3 text-right tnum">{r.games_played}</td>
                  <td className="px-4 py-3 text-right tnum text-rating">{r.wins}</td>
                  <td className="px-4 py-3 text-right tnum">
                    {r.win_rate != null ? `${r.win_rate}%` : "—"}
                  </td>
                  <td className="px-4 py-3 text-right tnum text-ink-dim">
                    {r.avg_rank ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {plays.length > 0 && (
        <>
          <h2 className="mt-10 mb-3 flex items-center gap-2 text-sm font-bold text-ink-dim">
            <Trophy size={15} /> 최근 판
          </h2>
          <ul className="flex flex-col gap-2">
            {plays.map((p) => {
              const winner = p.play_results.find((r) => r.rank === 1);
              return (
                <li
                  key={p.id}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl border border-line bg-panel px-4 py-3 text-sm"
                >
                  <span className="text-ink-faint tnum">{p.played_on}</span>
                  <span className="font-bold">{p.game_name}</span>
                  {winner && (
                    <span className="text-rating">
                      🏆 {winner.player_name}
                      {winner.score != null && ` (${winner.score})`}
                    </span>
                  )}
                  <span className="text-ink-faint tnum">
                    {p.play_results.length}인
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
