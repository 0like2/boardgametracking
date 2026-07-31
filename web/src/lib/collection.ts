"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Play log kept in localStorage.
 *
 * The site has no accounts (the list is public, only requests ask for a name),
 * so a visitor's collection lives on their own device. Logging a play is what
 * "unlocks" a game's card.
 */

const KEY = "boardgame.plays.v1";

export type Play = {
  gameId: string;
  /** ISO date, e.g. "2026-07-30" */
  date: string;
  players: number | null;
  /** Free text — winner, score, whatever the group cares about. */
  note: string;
};

function read(): Play[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as Play[]) : [];
  } catch {
    return [];
  }
}

function write(plays: Play[]): void {
  window.localStorage.setItem(KEY, JSON.stringify(plays));
  window.dispatchEvent(new Event("boardgame:plays"));
}

export function usePlays() {
  // Start empty so server and first client render agree, then hydrate.
  const [plays, setPlays] = useState<Play[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const sync = () => setPlays(read());
    sync();
    setLoaded(true);
    window.addEventListener("boardgame:plays", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("boardgame:plays", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const addPlay = useCallback((play: Play) => {
    write([play, ...read()]);
  }, []);

  const removePlay = useCallback((index: number) => {
    const next = read();
    next.splice(index, 1);
    write(next);
  }, []);

  const clearAll = useCallback(() => write([]), []);

  const playCount = useCallback(
    (gameId: string) => plays.filter((p) => p.gameId === gameId).length,
    [plays],
  );

  const playedIds = new Set(plays.map((p) => p.gameId));

  return { plays, playedIds, loaded, addPlay, removePlay, clearAll, playCount };
}
