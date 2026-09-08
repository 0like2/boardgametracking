import type { BookingInput } from "./azit";

/** Discord is the notification channel; durable reservation data lives in Supabase. */

export type RentalRequest = {
  type: "rental";
  name: string;
  contact: string;
  gameName: string;
  gameSlug: string;
  pickupDate: string;
  returnDate: string;
  note: string;
};

export type MeetupRequest = {
  type: "meetup";
  name: string;
  contact: string;
  /** Comma-joined weekdays, e.g. "토,일". Empty means any day works. */
  days: string;
  games: string;
};

export type SpaceRequest = BookingInput & {
  type: "space";
  bookingId: string;
  needsHost: boolean;
};

export type AppRequest = RentalRequest | MeetupRequest | SpaceRequest;

const SITE_NAME = "보드게임 컬렉션";

export function requestTitle(req: AppRequest): string {
  if (req.type === "space") return "🏠 아지트 예약 접수중";
  return req.type === "rental"
    ? `🎲 대여 예약 · ${req.gameName}`
    : `📣 모임 요청 · ${req.games || "게임 미지정"}`;
}

/** Space notifications omit personal details; the authenticated admin page has them. */
export function requestFields(req: AppRequest): [string, string][] {
  if (req.type === "space") {
    const format = new Intl.DateTimeFormat("ko-KR", {
      timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    });
    return [
      ["예약 번호", req.bookingId],
      ["시작 · 한국 시간", format.format(new Date(req.startAt))],
      ["종료 · 한국 시간", format.format(new Date(req.endAt))],
      ["인원", `${req.partySize}명 · 월 이용권 ${req.monthlyPassCount}명 (확인 필요)`],
      ["예상 1일 이용권 비용", `${((req.partySize - req.monthlyPassCount) * 5000).toLocaleString("ko-KR")}원`],
      ["주차", req.parking ? `${req.parking}대 · 사전 확인 필요` : "없음"],
      ["심야 동행", req.needsHost ? "00:10–09:00 운영자 동행 확인 필요" : "해당 없음"],
      ["예약 관리", "[신청 내용 확인 · 승인/취소](https://boardgame-collection-iota.vercel.app/azit/admin)"],
    ];
  }
  const common: [string, string][] = [
    ["신청자", req.name],
    ["연락처", req.contact],
  ];

  if (req.type === "rental") {
    return [
      ...common,
      ["게임", req.gameName],
      ["대여일", req.pickupDate || "미정"],
      ["반납일", req.returnDate || "미정"],
      ["메모", req.note || "—"],
    ];
  }

  return [
    ...common,
    ["하고 싶은 게임", req.games || "—"],
    ["가능한 요일", req.days ? `${req.days.split(",").join("·")}요일` : "아무 때나"],
  ];
}

async function sendDiscord(req: AppRequest, url: string): Promise<void> {
  const target = new URL(url);
  target.searchParams.set("wait", "true");
  const res = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(5000),
    body: JSON.stringify({
      username: SITE_NAME,
      allowed_mentions: { parse: [] },
      embeds: [
        {
          title: requestTitle(req),
          color: req.type === "rental" ? 0xf7861f : 0x4a9eff,
          fields: requestFields(req).map(([name, value]) => ({
            name,
            value: value || "—",
            inline: name !== "메모",
          })),
          timestamp: new Date().toISOString(),
        },
      ],
    }),
  });
  if (!res.ok) {
    throw new Error(`Discord webhook failed: ${res.status}`);
  }
}

/** Notification failure must not turn a successfully saved booking into a failed request. */
export async function notify(
  req: AppRequest,
): Promise<{ delivered: string[]; failed: string[] }> {
  const discordUrl = process.env.DISCORD_WEBHOOK_URL;
  if (!discordUrl) return { delivered: [], failed: [] };
  try {
    await sendDiscord(req, discordUrl);
    return { delivered: ["discord"], failed: [] };
  } catch {
    // Do not log the webhook URL, credentials or visitor details.
    console.error("[notify] discord delivery failed");
    return { delivered: [], failed: ["discord"] };
  }
}
