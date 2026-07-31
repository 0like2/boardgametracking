import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, FileText } from "lucide-react";

import { GameActions } from "@/components/GameActions";
import { GameCard } from "@/components/GameCard";
import {
  MATERIAL_KINDS,
  type MaterialKind,
  bestPlayersText,
  games,
  gamesBySlug,
  playersText,
  recPlayersText,
} from "@/lib/games";

export function generateStaticParams() {
  return games.map((g) => ({ slug: g.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const game = gamesBySlug.get(slug);
  if (!game) return { title: "게임을 찾을 수 없습니다" };
  return {
    title: `${game.nameKr} · 보드게임 컬렉션`,
    description: `${game.nameEn} — 난이도 ${game.weight ?? "—"} · ${game.minPlayers}~${game.maxPlayers}인`,
  };
}

export default async function GamePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const game = gamesBySlug.get(slug);
  if (!game) notFound();

  const byKind = new Map<MaterialKind, typeof game.materials>();
  for (const m of game.materials) {
    byKind.set(m.kind, [...(byKind.get(m.kind) ?? []), m]);
  }

  const linksByKind = new Map<MaterialKind, typeof game.boardlifeFiles>();
  for (const f of game.boardlifeFiles) {
    linksByKind.set(f.kind, [...(linksByKind.get(f.kind) ?? []), f]);
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <Link
        href="/"
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-ink-dim transition-colors hover:text-ink"
      >
        <ArrowLeft size={16} /> 목록으로
      </Link>

      <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_320px]">
        {/* --- left: the card --- */}
        <div className="order-2 flex flex-col gap-5 md:order-1">
          <GameCard game={game} full />

          {game.description && (
            <section className="rounded-2xl border border-line bg-panel p-5">
              <h2 className="mb-2 text-sm font-bold text-ink-dim">게임 소개</h2>
              <p className="text-sm leading-relaxed whitespace-pre-line text-ink">
                {game.description}
              </p>
              <p className="mt-3 text-xs text-ink-faint">출처 · 보드라이프</p>
            </section>
          )}
        </div>

        {/* --- right: details and actions --- */}
        <aside className="order-1 flex flex-col gap-5 md:order-2">
          <GameActions game={game} />

          <section className="rounded-2xl border border-line bg-panel p-4">
            <h2 className="mb-3 text-sm font-bold text-ink-dim">
              바로 받기{game.materials.length > 0 && ` (${game.materials.length})`}
            </h2>
            {game.materials.length === 0 ? (
              <p className="text-sm text-ink-faint">
                직접 올린 파일은 아직 없습니다. 아래 보드라이프 자료실을 확인해 주세요.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {MATERIAL_KINDS.filter((k) => byKind.has(k)).map((kind) => (
                  <div key={kind}>
                    <p className="mb-1.5 text-xs text-ink-faint">{kind}</p>
                    <ul className="flex flex-col gap-1.5">
                      {byKind.get(kind)!.map((m) => (
                        <li key={m.file}>
                          <a
                            href={m.file}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 rounded-lg bg-panel-2 px-3 py-2 text-sm transition-colors hover:bg-line"
                          >
                            <FileText size={15} className="shrink-0 text-ink-faint" />
                            <span className="min-w-0 flex-1 truncate">{m.label}</span>
                            <span className="shrink-0 text-[11px] text-ink-faint tnum">
                              {fileSize(m.size)}
                            </span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>

          {game.boardlifeFiles.length > 0 && (
            <section className="rounded-2xl border border-line bg-panel p-4">
              <h2 className="mb-1 text-sm font-bold text-ink-dim">
                보드라이프 자료실 ({game.boardlifeFiles.length})
              </h2>
              <p className="mb-3 text-xs text-ink-faint">
                보드라이프에서 직접 내려받는 링크입니다.
              </p>
              <div className="flex flex-col gap-3">
                {MATERIAL_KINDS.filter((k) => linksByKind.has(k)).map((kind) => (
                  <div key={kind}>
                    <p className="mb-1.5 text-xs text-ink-faint">{kind}</p>
                    <ul className="flex flex-col gap-1.5">
                      {linksByKind.get(kind)!.map((f) => (
                        <li key={f.url}>
                          <a
                            href={f.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-start gap-2 rounded-lg bg-panel-2 px-3 py-2 text-sm transition-colors hover:bg-line"
                          >
                            <ExternalLink
                              size={14}
                              className="mt-0.5 shrink-0 text-ink-faint"
                            />
                            <span className="min-w-0 flex-1">{f.label}</span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="rounded-2xl border border-line bg-panel p-4">
            <h2 className="mb-3 text-sm font-bold text-ink-dim">정보</h2>
            <dl className="flex flex-col gap-2 text-sm">
              <Row
                label="인원"
                value={
                  [
                    playersText(game),
                    bestPlayersText(game) && `베스트 ${bestPlayersText(game)}`,
                    recPlayersText(game) && `추천 ${recPlayersText(game)}`,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "—"
                }
              />
              <Row
                label="순위"
                value={
                  game.rank != null
                    ? `보드라이프 종합 ${game.rank.toLocaleString("ko")}위`
                    : "—"
                }
              />
              {game.baseGame && <Row label="확장" value={`「${game.baseGame}」의 확장`} />}
              <Row label="발매" value={game.year ? `${game.year}년` : "—"} />
              <Row label="분류" value={game.gameType || "—"} />
              <Row label="디자이너" value={game.designers.join(", ") || "—"} />
              <Row label="언어 의존도" value={game.languageDependence ?? "—"} />
              <Row
                label="테마"
                value={game.categories.join(", ") || "—"}
              />
              <Row
                label="진행 방식"
                value={game.mechanics.join(", ") || "—"}
              />
            </dl>
          </section>

          <section className="flex flex-col gap-1.5">
            <a
              href={game.boardlifeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-ink-dim transition-colors hover:text-ink"
            >
              <ExternalLink size={14} /> 보드라이프에서 보기
            </a>
            {game.bggId && (
              <a
                href={`https://boardgamegeek.com/boardgame/${game.bggId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-ink-dim transition-colors hover:text-ink"
              >
                <ExternalLink size={14} /> BoardGameGeek에서 보기
              </a>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

/** Small files round to "0.0MB", which reads as broken — show KB instead. */
function fileSize(bytes: number): string {
  return bytes < 1e6 ? `${Math.round(bytes / 1e3)}KB` : `${(bytes / 1e6).toFixed(1)}MB`;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <dt className="w-20 shrink-0 text-ink-faint">{label}</dt>
      <dd className="min-w-0 flex-1 text-ink">{value}</dd>
    </div>
  );
}
