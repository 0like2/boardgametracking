import assert from "node:assert/strict";
import test from "node:test";
import { notify, requestFields, type AppRequest } from "../src/lib/notify.ts";

const request: AppRequest = { type: "meetup", name: "test", contact: "당근 test", days: "토", games: "티츄" };

test("Discord is the only notification channel even when legacy SMTP settings remain", async () => {
  const originalFetch = globalThis.fetch;
  const originalWebhook = process.env.DISCORD_WEBHOOK_URL;
  const originalSmtp = process.env.SMTP_PASSWORD;
  try {
    process.env.SMTP_PASSWORD = "unused-test-password";
    delete process.env.DISCORD_WEBHOOK_URL;
    globalThis.fetch = async () => { throw new Error("no external call expected"); };
    assert.deepEqual(await notify(request), { delivered: [], failed: [] });

    process.env.DISCORD_WEBHOOK_URL = "https://discord.invalid/api/webhooks/test/token";
    let calls = 0;
    globalThis.fetch = async (url, options) => {
      assert.equal(new URL(String(url)).hostname, "discord.invalid");
      assert.equal(new URL(String(url)).searchParams.get("wait"), "true");
      const payload = JSON.parse(String(options?.body));
      assert.deepEqual(payload.allowed_mentions, { parse: [] });
      assert.ok(options?.signal);
      calls += 1;
      return new Response("{}", { status: 200 });
    };
    assert.deepEqual(await notify(request), { delivered: ["discord"], failed: [] });
    assert.equal(calls, 1);
    assert.ok(requestFields(request).some(([label, value]) => label === "가능한 요일" && value === "토요일"));

    globalThis.fetch = async () => { throw new Error("timeout"); };
    assert.deepEqual(await notify(request), { delivered: [], failed: ["discord"] });
  } finally {
    globalThis.fetch = originalFetch;
    if (originalWebhook === undefined) delete process.env.DISCORD_WEBHOOK_URL;
    else process.env.DISCORD_WEBHOOK_URL = originalWebhook;
    if (originalSmtp === undefined) delete process.env.SMTP_PASSWORD;
    else process.env.SMTP_PASSWORD = originalSmtp;
  }
});
