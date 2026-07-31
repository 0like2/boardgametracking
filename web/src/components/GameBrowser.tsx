"use client";

import { useMemo, useState } from "react";
import { Search, X } from "lucide-react";

import { type Game, type PlayerFit, materialCount, playerFit } from "@/lib/games";
import { GameCard } from "./GameCard";
import { GameSheet } from "./GameSheet";

type Sort = "name" | "weight" | "weightDesc" | "rating" | "year";

const WEIGHT_BANDS = [
  { key: "light", label: "입문 ~2.0", min: 0, max: 2 },
  { key: "mid", label: "가벼움 2~2.5", min: 2, max: 2.5 },
  { key: "heavy", label: "중급 2.5~3.5", min: 2.5, max: 3.5 },
  { key: "brain", label: "헤비 3.5~", min: 3.5, max: 99 },
] as const;

const TIME_BANDS = [
  { key: "t30", label: "~30분", min: 0, max: 30 },
  { key: "t60", label: "30~60분", min: 30, max: 60 },
  { key: "t120", label: "60~120분", min: 60, max: 120 },
  { key: "tlong", label: "120분~", min: 120, max: 99999 },
] as const;

const PLAYER_CHOICES = [1, 2, 3, 4, 5, 6, 7, 8];

/** How strict the player-count filter is. */
type FitLevel = "ok" | "rec" | "best";

const FIT_LEVELS: { key: FitLevel; label: string; hint: string }[] = [
  { key: "ok", label: "가능", hint: "인원 범위 안에 드는 게임" },
  { key: "rec", label: "추천 이상", hint: "추천 또는 베스트 인원" },
  { key: "best", label: "베스트만", hint: "이 인원이 베스트인 게임" },
];

const FIT_RANK: Record<PlayerFit, number> = { no: 0, ok: 1, rec: 2, best: 3 };

export function GameBrowser({ games, gameTypes }: { games: Game[]; gameTypes: string[] }) {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<number | null>(null);
  const [fitLevel, setFitLevel] = useState<FitLevel>("ok");
  const [weightBands, setWeightBands] = useState<string[]>([]);
  const [timeBands, setTimeBands] = useState<string[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const [materialsOnly, setMaterialsOnly] = useState(false);
  const [hideExpansions, setHideExpansions] = useState(false);
  const [sort, setSort] = useState<Sort>("name");
  const [selected, setSelected] = useState<Game | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    const result = games.filter((g) => {
      if (q) {
        const hay = `${g.nameKr} ${g.nameEn} ${g.designers.join(" ")}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (players != null && FIT_RANK[playerFit(g, players)] < FIT_RANK[fitLevel]) {
        return false;
      }
      if (weightBands.length > 0) {
        if (g.weight == null) return false;
        const hit = WEIGHT_BANDS.some(
          (b) => weightBands.includes(b.key) && g.weight! >= b.min && g.weight! < b.max,
        );
        if (!hit) return false;
      }
      if (timeBands.length > 0) {
        const t = g.maxTime ?? g.minTime;
        if (t == null) return false;
        const hit = TIME_BANDS.some(
          (b) => timeBands.includes(b.key) && t > b.min && t <= b.max,
        );
        if (!hit) return false;
      }
      if (types.length > 0 && !types.includes(g.gameType)) return false;
      if (materialsOnly && materialCount(g) === 0) return false;
      if (hideExpansions && g.baseGame) return false;
      return true;
    });

    const byName = (a: Game, b: Game) => a.nameKr.localeCompare(b.nameKr, "ko");
    result.sort((a, b) => {
      // With a player count chosen, the best fits float to the top regardless
      // of the secondary sort — that is the question the filter is answering.
      if (players != null) {
        const diff = FIT_RANK[playerFit(b, players)] - FIT_RANK[playerFit(a, players)];
        if (diff !== 0) return diff;
      }
      switch (sort) {
        case "weight":
          return (a.weight ?? 99) - (b.weight ?? 99) || byName(a, b);
        case "weightDesc":
          return (b.weight ?? -1) - (a.weight ?? -1) || byName(a, b);
        case "rating":
          return (b.rating ?? -1) - (a.rating ?? -1) || byName(a, b);
        case "year":
          return (b.year ?? 0) - (a.year ?? 0) || byName(a, b);
        default:
          return byName(a, b);
      }
    });
    return result;
  }, [
    games,
    query,
    players,
    fitLevel,
    weightBands,
    timeBands,
    types,
    materialsOnly,
    hideExpansions,
    sort,
  ]);

  const activeCount =
    (query ? 1 : 0) +
    (players != null ? 1 : 0) +
    weightBands.length +
    timeBands.length +
    types.length +
    (materialsOnly ? 1 : 0) +
    (hideExpansions ? 1 : 0);

  function reset() {
    setQuery("");
    setPlayers(null);
    setFitLevel("ok");
    setWeightBands([]);
    setTimeBands([]);
    setTypes([]);
    setMaterialsOnly(false);
    setHideExpansions(false);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* --- search --- */}
      <div className="relative mb-4">
        <Search
          size={18}
          className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-ink-faint"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="게임 이름 또는 디자이너 검색"
          className="w-full rounded-xl border border-line bg-panel py-3 pr-4 pl-11 text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
        />
      </div>

      {/* --- player count --- */}
      <FilterRow label="인원">
        {PLAYER_CHOICES.map((n) => (
          <Chip
            key={n}
            active={players === n}
            onClick={() => setPlayers(players === n ? null : n)}
          >
            {n}인
          </Chip>
        ))}
      </FilterRow>

      {players != null && (
        <FilterRow label="">
          {FIT_LEVELS.map((f) => (
            <Chip
              key={f.key}
              active={fitLevel === f.key}
              onClick={() => setFitLevel(f.key)}
              accent={fitLevel === f.key && f.key !== "ok"}
              title={f.hint}
            >
              {f.key === "best" ? "★ " : ""}
              {f.label}
            </Chip>
          ))}
        </FilterRow>
      )}

      <FilterRow label="난이도">
        {WEIGHT_BANDS.map((b) => (
          <Chip
            key={b.key}
            active={weightBands.includes(b.key)}
            onClick={() => setWeightBands(toggle(weightBands, b.key))}
          >
            {b.label}
          </Chip>
        ))}
      </FilterRow>

      <FilterRow label="시간">
        {TIME_BANDS.map((b) => (
          <Chip
            key={b.key}
            active={timeBands.includes(b.key)}
            onClick={() => setTimeBands(toggle(timeBands, b.key))}
          >
            {b.label}
          </Chip>
        ))}
      </FilterRow>

      <FilterRow label="분류">
        {gameTypes.map((t) => (
          <Chip key={t} active={types.includes(t)} onClick={() => setTypes(toggle(types, t))}>
            {t}
          </Chip>
        ))}
        <Chip active={materialsOnly} onClick={() => setMaterialsOnly(!materialsOnly)}>
          📄 자료 있는 것만
        </Chip>
        <Chip active={hideExpansions} onClick={() => setHideExpansions(!hideExpansions)}>
          확장 제외
        </Chip>
      </FilterRow>

      {/* --- result bar --- */}
      <div className="mt-5 mb-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
        <p className="text-sm text-ink-dim">
          <strong className="text-ink tnum">{filtered.length}</strong>개
          {players != null && (
            <span className="text-ink-faint">
              {" "}
              · {players}인 {FIT_LEVELS.find((f) => f.key === fitLevel)!.label}
            </span>
          )}
        </p>

        {activeCount > 0 && (
          <button
            onClick={reset}
            className="inline-flex items-center gap-1 rounded-lg bg-panel px-2.5 py-1 text-xs text-ink-dim transition-colors hover:text-ink"
          >
            <X size={12} /> 필터 {activeCount}개 초기화
          </button>
        )}

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className="ml-auto rounded-lg border border-line bg-panel px-3 py-1.5 text-sm text-ink focus:border-accent focus:outline-none"
        >
          <option value="name">이름순</option>
          <option value="weight">난이도 낮은순</option>
          <option value="weightDesc">난이도 높은순</option>
          <option value="rating">평점순</option>
          <option value="year">최신순</option>
        </select>
      </div>

      {/* --- grid --- */}
      {filtered.length === 0 ? (
        <p className="py-20 text-center text-ink-faint">
          조건에 맞는 게임이 없습니다. 필터를 줄여보세요.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {filtered.map((g) => (
            <GameCard
              key={g.id}
              game={g}
              onClick={() => setSelected(g)}
              fit={players != null ? playerFit(g, players) : undefined}
            />
          ))}
        </div>
      )}

      {selected && <GameSheet game={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function toggle(list: string[], key: string): string[] {
  return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center gap-3">
      <span className="w-11 shrink-0 text-xs text-ink-faint">{label}</span>
      <div className="no-scrollbar flex gap-1.5 overflow-x-auto py-0.5">{children}</div>
    </div>
  );
}

function Chip({
  active,
  accent,
  onClick,
  title,
  children,
}: {
  active: boolean;
  accent?: boolean;
  onClick: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  const on = accent
    ? "bg-rating text-black font-medium"
    : "bg-ink text-bg font-medium";
  return (
    <button
      onClick={onClick}
      title={title}
      className={`shrink-0 rounded-full px-3 py-1.5 text-xs whitespace-nowrap transition-colors ${
        active ? on : "bg-panel text-ink-dim hover:bg-panel-2 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
