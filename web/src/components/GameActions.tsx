"use client";

import { useState } from "react";
import { CalendarPlus, PackageOpen, Sparkles } from "lucide-react";

import type { Game } from "@/lib/games";
import { usePlays } from "@/lib/collection";
import { GameSheet } from "./GameSheet";

/** The three primary actions, shown on the game detail page. */
export function GameActions({ game }: { game: Game }) {
  const [open, setOpen] = useState(false);
  const { playCount, loaded } = usePlays();
  const count = playCount(game.id);

  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        <button
          onClick={() => setOpen(true)}
          className="flex flex-col items-center gap-1.5 rounded-xl bg-weight px-3 py-3 text-xs font-bold text-black transition-opacity hover:opacity-90"
        >
          <PackageOpen size={20} /> 대여 예약
        </button>
        <button
          onClick={() => setOpen(true)}
          className="flex flex-col items-center gap-1.5 rounded-xl bg-accent px-3 py-3 text-xs font-bold text-white transition-opacity hover:opacity-90"
        >
          <CalendarPlus size={20} /> 모임 열어주세요
        </button>
        <button
          onClick={() => setOpen(true)}
          className="flex flex-col items-center gap-1.5 rounded-xl border border-line bg-panel px-3 py-3 text-xs font-bold text-ink transition-colors hover:bg-panel-2"
        >
          <Sparkles size={20} />
          {loaded && count > 0 ? `${count}회 기록됨` : "플레이 기록"}
        </button>
      </div>

      {open && <GameSheet game={game} onClose={() => setOpen(false)} />}
    </>
  );
}
