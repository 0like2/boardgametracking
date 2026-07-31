/**
 * Fan a submitted request out to Discord and email.
 *
 * Every channel is optional: a channel with no env var configured is skipped
 * rather than failing the request, so the site keeps working before the
 * webhook/API key are filled in.
 */

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

export type AppRequest = RentalRequest | MeetupRequest;

const SITE_NAME = "보드게임 컬렉션";

export function requestTitle(req: AppRequest): string {
  return req.type === "rental"
    ? `🎲 대여 예약 · ${req.gameName}`
    : `📣 모임 요청 · ${req.games || "게임 미지정"}`;
}

/** Ordered label/value pairs, shared by the Discord embed and the email. */
export function requestFields(req: AppRequest): [string, string][] {
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
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: SITE_NAME,
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
    throw new Error(`Discord webhook failed: ${res.status} ${await res.text()}`);
  }
}

/** Gmail SMTP with an app password — the same account the Python scraper uses. */
async function sendEmail(req: AppRequest, password: string): Promise<void> {
  const user = process.env.SMTP_USER;
  const to = process.env.NOTIFY_EMAIL_TO ?? user;
  if (!user) throw new Error("SMTP_USER is not set");
  if (!to) throw new Error("NOTIFY_EMAIL_TO is not set");

  const rows = requestFields(req)
    .map(
      ([k, v]) =>
        `<tr><td style="padding:6px 14px 6px 0;color:#777;white-space:nowrap">${escapeHtml(
          k,
        )}</td><td style="padding:6px 0"><b>${escapeHtml(v)}</b></td></tr>`,
    )
    .join("");

  // Imported lazily so the module stays out of the bundle when email is off.
  const nodemailer = (await import("nodemailer")).default;
  const transport = nodemailer.createTransport({
    host: process.env.SMTP_HOST ?? "smtp.gmail.com",
    port: Number(process.env.SMTP_PORT ?? 587),
    secure: false, // STARTTLS on 587
    auth: { user, pass: password },
  });

  await transport.sendMail({
    from: `${SITE_NAME} <${user}>`,
    to,
    subject: requestTitle(req),
    html: `<div style="font-family:system-ui,sans-serif;font-size:15px">
      <h2 style="margin:0 0 14px">${escapeHtml(requestTitle(req))}</h2>
      <table style="border-collapse:collapse">${rows}</table>
    </div>`,
  });
}

/**
 * Deliver to every configured channel. Returns which ones succeeded so the
 * caller can tell the visitor the request actually landed somewhere.
 */
export async function notify(
  req: AppRequest,
): Promise<{ delivered: string[]; failed: string[] }> {
  const jobs: [string, Promise<void>][] = [];

  const discordUrl = process.env.DISCORD_WEBHOOK_URL;
  if (discordUrl) jobs.push(["discord", sendDiscord(req, discordUrl)]);

  const smtpPassword = process.env.SMTP_PASSWORD;
  if (smtpPassword) jobs.push(["email", sendEmail(req, smtpPassword)]);

  const results = await Promise.allSettled(jobs.map(([, p]) => p));
  const delivered: string[] = [];
  const failed: string[] = [];

  results.forEach((r, i) => {
    const channel = jobs[i][0];
    if (r.status === "fulfilled") {
      delivered.push(channel);
    } else {
      failed.push(channel);
      console.error(`[notify] ${channel} failed:`, r.reason);
    }
  });

  return { delivered, failed };
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
