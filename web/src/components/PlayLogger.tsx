"use client";

import { useState } from "react";
import { CalendarPlus } from "lucide-react";

import type { Game } from "@/lib/games";
import { usePlays } from "@/lib/collection";

export function PlayLogger({ game, onDone }: { game: Game; onDone: () => void }) {
  const { addPlay } = usePlays();
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [players, setPlayers] = useState<number | null>(game.bestPlayers[0] ?? null);
  const [note, setNote] = useState("");

  const choices = Array.from(
    { length: game.maxPlayers - game.minPlayers + 1 },
    (_, i) => game.minPlayers + i,
  );

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        addPlay({ gameId: game.id, date, players, note: note.trim() });
        onDone();
      }}
      className="flex flex-col gap-4"
    >
      <label className="flex flex-col gap-1.5">
        <span className="text-xs text-ink-dim">플레이 날짜</span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-xl border border-line bg-panel px-3.5 py-2.5 text-ink focus:border-accent focus:outline-none"
        />
      </label>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-ink-dim">인원</span>
        <div className="flex flex-wrap gap-1.5">
          {choices.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setPlayers(n === players ? null : n)}
              className={`rounded-full px-3.5 py-1.5 text-sm transition-colors ${
                players === n
                  ? "bg-ink font-medium text-bg"
                  : "bg-panel text-ink-dim hover:bg-panel-2"
              }`}
            >
              {n}인{game.bestPlayers.includes(n) && " ⭐"}
            </button>
          ))}
        </div>
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs text-ink-dim">메모</span>
        <textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="누가 이겼는지, 점수, 기억에 남는 순간"
          className="rounded-xl border border-line bg-panel px-3.5 py-2.5 text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
        />
      </label>

      <p className="text-xs text-ink-faint">
        기록은 이 기기에만 저장됩니다. 기록하면 「내 카드」에서 이 게임 카드가 열립니다.
      </p>

      <button
        type="submit"
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 font-bold text-white transition-opacity hover:opacity-90"
      >
        <CalendarPlus size={18} /> 기록하고 카드 획득
      </button>
    </form>
  );
}
