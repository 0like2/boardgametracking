import Image from "next/image";
import Link from "next/link";
import { Users, Layers, Clock, Trophy } from "lucide-react";

import {
  type Game,
  type PlayerFit,
  FIT_LABEL,
  bestPlayersText,
  coverSrc,
  materialCount,
  playersText,
  recPlayersText,
  timeText,
} from "@/lib/games";
import { Gauge } from "./Gauge";

type Props = {
  game: Game;
  /** Grid tiles are compact; the detail page uses the full print-style card. */
  full?: boolean;
  /** Dim + desaturate games the visitor has not logged a play for. */
  locked?: boolean;
  href?: string;
  onClick?: () => void;
  /** When a player count is being filtered on, show how well it fits. */
  fit?: PlayerFit;
};

const FIT_CLASS: Record<PlayerFit, string> = {
  best: "bg-rating text-black",
  rec: "bg-accent text-white",
  ok: "bg-black/65 text-ink-dim",
  no: "bg-black/65 text-ink-faint",
};

export function GameCard({
  game,
  full = false,
  locked = false,
  href,
  onClick,
  fit,
}: Props) {
  const interactive = Boolean(href || onClick);

  const card = (
    <article
      className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-panel text-left transition-all ${
        interactive
          ? "hover:-translate-y-1 hover:border-ink-faint hover:shadow-xl hover:shadow-black/40"
          : ""
      } ${locked ? "opacity-45 grayscale" : ""}`}
    >
      {/* --- poster --- */}
      <div className={`relative w-full overflow-hidden ${full ? "aspect-4/3" : "aspect-square"}`}>
        <Image
          src={coverSrc(game)}
          alt={game.nameKr}
          fill
          sizes={full ? "(max-width: 768px) 100vw, 480px" : "(max-width: 640px) 50vw, 260px"}
          className="object-cover transition-transform duration-500 group-hover:scale-[1.04]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-panel via-panel/25 to-transparent" />

        <div className="absolute top-2 right-2 flex flex-col items-end gap-1">
          {fit && fit !== "no" && (
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-bold backdrop-blur-sm ${FIT_CLASS[fit]}`}
            >
              {FIT_LABEL[fit]}
            </span>
          )}
          {materialCount(game) > 0 && (
            <span className="rounded-full bg-black/65 px-2 py-0.5 text-[10px] font-medium text-ink backdrop-blur-sm">
              자료 {materialCount(game)}
            </span>
          )}
          {game.baseGame && (
            <span className="rounded-full bg-black/65 px-2 py-0.5 text-[10px] font-medium text-ink-dim backdrop-blur-sm">
              확장
            </span>
          )}
        </div>

        {/* The blurb sits over the art. On the big card it is always visible;
            on grid tiles the whole poster flips to an info panel on hover. */}
        {full ? (
          game.summary && (
            <p className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/70 to-transparent px-3 pt-8 pb-2.5 text-sm leading-snug text-ink">
              {game.summary}
            </p>
          )
        ) : (
          <InfoOverlay game={game} />
        )}
      </div>

      {/* --- body --- */}
      <div className={`flex flex-1 flex-col ${full ? "gap-4 p-5" : "gap-2.5 p-3"}`}>
        <div>
          {full && game.categories.length > 0 && (
            <p className="mb-1 text-xs text-ink-faint">
              {game.categories.slice(0, 2).join(" · ")}
            </p>
          )}
          <h3
            className={`leading-tight font-black text-ink ${
              full ? "text-2xl" : "line-clamp-2 text-sm"
            }`}
          >
            {game.nameKr}
          </h3>
          <p
            className={`text-rating ${
              full ? "mt-1 text-base" : "line-clamp-1 text-[11px]"
            }`}
          >
            {game.nameEn}
          </p>
        </div>

        <div className={`flex flex-col ${full ? "gap-2" : "gap-1.5"}`}>
          <Gauge
            label="난이도"
            value={game.weight}
            max={5}
            color="var(--weight)"
            ticks={full ? [0, 1, 2, 3, 4, 5] : undefined}
            compact={!full}
          />
          <Gauge
            label="평점"
            value={game.rating}
            max={10}
            color="var(--rating)"
            ticks={full ? [0, 2, 4, 6, 8, 10] : undefined}
            compact={!full}
          />
        </div>

        {full ? (
          <>
            <hr className="border-line" />
            <div className="grid grid-cols-3 divide-x divide-line text-center">
              <Stat icon={<Users size={22} />} label="인원" value={playersText(game)}>
                {bestPlayersText(game) && <>베스트 {bestPlayersText(game)}</>}
              </Stat>
              <Stat icon={<Layers size={22} />} label="메커니즘" value="">
                <span className="flex flex-wrap justify-center gap-1">
                  {game.mechanics.slice(0, 2).map((m) => (
                    <span
                      key={m}
                      className="rounded-full bg-panel-2 px-2 py-0.5 text-[11px] text-ink-dim"
                    >
                      {m}
                    </span>
                  ))}
                </span>
              </Stat>
              <Stat icon={<Clock size={22} />} label="시간" value={timeText(game)}>
                {game.minAge != null && <>{game.minAge}세 이상</>}
              </Stat>
            </div>
          </>
        ) : (
          <div className="mt-auto flex items-center justify-between text-[11px] text-ink-dim tnum">
            <span className="inline-flex items-center gap-1">
              <Users size={12} />
              {playersText(game)}
            </span>
            {bestPlayersText(game) && (
              <span className="text-rating">★{bestPlayersText(game)}</span>
            )}
            <span className="inline-flex items-center gap-1">
              <Clock size={12} />
              {timeText(game)}
            </span>
          </div>
        )}
      </div>
    </article>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="block h-full w-full">
        {card}
      </button>
    );
  }

  return href ? (
    <Link href={href} className="block h-full">
      {card}
    </Link>
  ) : (
    card
  );
}

/**
 * Slides up over the poster on hover. Pointer-events stay off so the click
 * still reaches the card underneath, and it is hidden from touch devices
 * (where a tap opens the sheet instead).
 */
function InfoOverlay({ game }: { game: Game }) {
  return (
    <div className="pointer-events-none absolute inset-0 hidden flex-col justify-end gap-1.5 bg-gradient-to-t from-black via-black/90 to-black/60 p-3 opacity-0 transition-opacity duration-300 group-hover:opacity-100 sm:flex">
      {game.summary && (
        <p className="line-clamp-4 text-[11px] leading-snug text-ink">{game.summary}</p>
      )}

      <dl className="flex flex-col gap-0.5 text-[10px] leading-tight">
        {bestPlayersText(game) && (
          <Line label="베스트" value={bestPlayersText(game)} tone="text-rating" />
        )}
        {recPlayersText(game) && (
          <Line label="추천" value={recPlayersText(game)} tone="text-accent" />
        )}
        {game.mechanics.length > 0 && (
          <Line label="방식" value={game.mechanics.slice(0, 2).join(", ")} />
        )}
        {game.designers.length > 0 && (
          <Line label="디자이너" value={game.designers.slice(0, 2).join(", ")} />
        )}
      </dl>

      {game.rank != null && (
        <p className="flex items-center gap-1 text-[10px] text-ink-faint tnum">
          <Trophy size={10} /> 보드라이프 종합 {game.rank.toLocaleString("ko")}위
        </p>
      )}
    </div>
  );
}

function Line({
  label,
  value,
  tone = "text-ink-dim",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex gap-1.5">
      <dt className="w-11 shrink-0 text-ink-faint">{label}</dt>
      <dd className={`min-w-0 flex-1 truncate ${tone}`}>{value}</dd>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-1 px-2">
      <span className="text-ink-faint">{icon}</span>
      <span className="text-[11px] text-ink-dim">{label}</span>
      {value && <span className="text-lg font-black text-ink tnum">{value}</span>}
      <span className="text-[11px] text-ink-faint">{children}</span>
    </div>
  );
}
