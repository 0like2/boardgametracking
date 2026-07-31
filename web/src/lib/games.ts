import rawGames from "../../data/games.json";
import rawMaterials from "../../data/materials.json";

export type Material = {
  /** 점수판 | 개인판 | 요약표 | 참조표 | 룰북 | 기타 */
  kind: MaterialKind;
  label: string;
  file: string;
  /** bytes, for showing a download size hint */
  size: number;
};

export const MATERIAL_KINDS = [
  "점수판",
  "개인판",
  "요약표",
  "참조표",
  "룰북",
  "한글화",
  "기타",
] as const;

export type MaterialKind = (typeof MATERIAL_KINDS)[number];

/** An entry in Boardlife's 자료실 — a link out, not a file we host. */
export type BoardlifeFile = {
  kind: MaterialKind;
  category: string;
  label: string;
  url: string;
};

export type Game = {
  id: string;
  slug: string;
  bggId: number | null;
  nameKr: string;
  nameEn: string;
  /** One-line teaser shown over the cover art. May be empty. */
  summary: string;
  /** Full Korean blurb from Boardlife. May be empty. */
  description: string;
  /** Set when this title is an expansion of another game in the collection. */
  baseGame: string | null;
  year: number | null;
  batch: string;
  minPlayers: number;
  maxPlayers: number;
  bestPlayers: number[];
  /** Counts Boardlife marks as 추천 — good, but not the single best count. */
  recPlayers: number[];
  /** Boardlife overall rank (1 = highest). */
  rank: number | null;
  minTime: number | null;
  maxTime: number | null;
  minAge: number | null;
  weight: number | null;
  rating: number | null;
  gameType: string;
  categories: string[];
  mechanics: string[];
  designers: string[];
  languageDependence: string | null;
  imageUrl: string;
  boardlifeUrl: string;
  /** Links into Boardlife's 자료실 for this game. */
  boardlifeFiles: BoardlifeFile[];
  /** Files we host ourselves, downloadable directly. */
  materials: Material[];
};

/** Total resources on offer, hosted plus linked. */
export function materialCount(game: Game): number {
  return game.materials.length + game.boardlifeFiles.length;
}

const materialsById = rawMaterials as Record<string, Material[]>;

export const games: Game[] = (rawGames as Omit<Game, "materials">[]).map((g) => ({
  ...g,
  materials: materialsById[g.id] ?? [],
}));

export const gamesBySlug = new Map(games.map((g) => [g.slug, g]));

export function coverSrc(game: Game): string {
  return `/covers/${game.id}.jpg`;
}

/** BGG weight is 1..5; render it as a 0..100 gauge. */
export function weightPct(weight: number | null): number {
  if (weight == null) return 0;
  return Math.max(0, Math.min(100, (weight / 5) * 100));
}

export function ratingPct(rating: number | null): number {
  if (rating == null) return 0;
  return Math.max(0, Math.min(100, (rating / 10) * 100));
}

export function playersText(game: Game): string {
  return game.minPlayers === game.maxPlayers
    ? `${game.minPlayers}인`
    : `${game.minPlayers}~${game.maxPlayers}인`;
}

export function bestPlayersText(game: Game): string {
  if (game.bestPlayers.length === 0) return "";
  const b = game.bestPlayers;
  const contiguous = b.every((n, i) => i === 0 || n === b[i - 1] + 1);
  return contiguous && b.length > 1
    ? `${b[0]}~${b[b.length - 1]}인`
    : b.join("·") + "인";
}

export function timeText(game: Game): string {
  const { minTime, maxTime } = game;
  if (minTime == null && maxTime == null) return "—";
  if (minTime != null && maxTime != null && minTime !== maxTime) {
    return `${minTime}~${maxTime}분`;
  }
  return `${maxTime ?? minTime}분`;
}

/** Does this game support exactly `count` players? */
export function supportsCount(game: Game, count: number): boolean {
  return count >= game.minPlayers && count <= game.maxPlayers;
}

export function isBestAt(game: Game, count: number): boolean {
  return game.bestPlayers.includes(count);
}

export type PlayerFit = "best" | "rec" | "ok" | "no";

/** How well the game plays at exactly `count` players. */
export function playerFit(game: Game, count: number): PlayerFit {
  if (game.bestPlayers.includes(count)) return "best";
  if (game.recPlayers.includes(count)) return "rec";
  return supportsCount(game, count) ? "ok" : "no";
}

export const FIT_LABEL: Record<PlayerFit, string> = {
  best: "베스트",
  rec: "추천",
  ok: "가능",
  no: "불가",
};

export function recPlayersText(game: Game): string {
  if (game.recPlayers.length === 0) return "";
  const r = game.recPlayers;
  const contiguous = r.every((n, i) => i === 0 || n === r[i - 1] + 1);
  return contiguous && r.length > 1
    ? `${r[0]}~${r[r.length - 1]}인`
    : r.join("·") + "인";
}

/** Every distinct category across the collection, most common first. */
export function allCategories(): string[] {
  return rankedValues((g) => g.categories);
}

export function allMechanics(): string[] {
  return rankedValues((g) => g.mechanics);
}

export function allGameTypes(): string[] {
  return rankedValues((g) => (g.gameType ? [g.gameType] : []));
}

function rankedValues(pick: (g: Game) => string[]): string[] {
  const counts = new Map<string, number>();
  for (const g of games) {
    for (const v of pick(g)) counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko"))
    .map(([v]) => v);
}
